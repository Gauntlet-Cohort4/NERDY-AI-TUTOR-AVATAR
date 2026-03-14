"""SubjectTutorAgent — base class for subject-specific tutor agents.

Provides STT keyterm update on subject handoff via _update_stt_keyterms().
Each subclass sets _subject to its Subject enum value.

Whiteboard tools (show_equation, show_diagram, show_interactive,
generate_visual) are registered as function_tools so the LLM can invoke
them during a tutoring session.  Payloads are published to the LiveKit
data channel on the ``"whiteboard"`` topic.
"""

from __future__ import annotations

import json

import structlog
from livekit.agents import Agent, RunContext, function_tool

from src.db.visuals import get_visual
from src.education.subjects import get_keyterms
from src.types import Subject
from src.visuals.templates import TEMPLATES

logger = structlog.get_logger(__name__)

# Data channel topic the frontend whiteboard subscribes to
_WHITEBOARD_TOPIC = "whiteboard"

# Maximum visual content size (512 KB)
MAX_CONTENT_BYTES = 512 * 1024


class SubjectTutorAgent(Agent):
    """Base class for subject-specific tutor agents.

    Subclasses must set the _subject class attribute to the appropriate
    Subject enum value. Call _update_stt_keyterms() in on_enter() to
    update Deepgram STT keyterms for the active subject.
    """

    _subject: Subject  # Must be set by subclass
    _grade: int | None = None  # Optional grade override from frontend

    def _update_stt_keyterms(self) -> None:
        """Update Deepgram STT keyterms for this subject.

        Handles gracefully:
        - session.stt is None
        - session has no stt attribute
        - stt has no update_options method
        """
        stt = getattr(self.session, "stt", None)
        if stt is not None and hasattr(stt, "update_options"):
            keyterms = get_keyterms(self._subject)
            stt.update_options(keyterm=keyterms)
            logger.info(
                "stt_keyterms_updated",
                subject=self._subject.value,
                count=len(keyterms),
            )

    # ------------------------------------------------------------------
    # Whiteboard function tools
    # ------------------------------------------------------------------

    @function_tool
    async def show_equation(
        self,
        ctx: RunContext,
        latex: str,
        title: str = "",
    ) -> str:
        """Display a math equation on the whiteboard.

        Args:
            latex: LaTeX string to render (e.g., '\\frac{1}{2}')
            title: Optional label shown above the equation
        """
        payload = {"type": "equation", "latex": latex, "title": title}
        if not await self._publish_whiteboard(payload):
            return "Failed to publish equation to whiteboard."
        return f"Equation displayed: {title or latex[:40]}"

    @function_tool
    async def show_diagram(
        self,
        ctx: RunContext,
        topic_key: str,
    ) -> str:
        """Show a pre-cached diagram or image on the whiteboard.

        Args:
            topic_key: Topic identifier (e.g., 'cell_structure', 'newtons_third_law')
        """
        asset = await self._lookup_visual(topic_key)
        if not asset:
            return f"No diagram found for '{topic_key}'. Try generate_visual instead."
        content = asset["content"]
        if isinstance(content, str) and len(content.encode()) > MAX_CONTENT_BYTES:
            logger.warning(
                "visual_content_too_large",
                topic_key=topic_key,
                size=len(content.encode()),
            )
            return f"Diagram '{asset['title']}' is too large to display. Try generate_visual instead."
        payload = {
            "type": asset["asset_type"],
            "content": content,
            "title": asset["title"],
            "alt_text": (asset.get("metadata") or {}).get("alt_text", ""),
        }
        if not await self._publish_whiteboard(payload):
            return "Failed to publish diagram to whiteboard."
        return f"Diagram displayed: {asset['title']}"

    @function_tool
    async def show_interactive(
        self,
        ctx: RunContext,
        template_id: str,
        params: str,
    ) -> str:
        """Show an interactive diagram template with specific parameters.

        Args:
            template_id: Template name (e.g., 'number_line', 'coordinate_plane')
            params: JSON string of template parameters
        """
        if template_id not in TEMPLATES:
            return f"Unknown template '{template_id}'. Available: {', '.join(TEMPLATES)}"
        try:
            parsed_params = json.loads(params)
        except json.JSONDecodeError:
            return "Invalid params JSON. Please provide valid JSON."
        payload = {
            "type": "interactive",
            "template_id": template_id,
            "params": parsed_params,
        }
        if not await self._publish_whiteboard(payload):
            return "Failed to publish interactive diagram to whiteboard."
        return f"Interactive diagram displayed: {template_id}"

    @function_tool
    async def generate_visual(
        self,
        ctx: RunContext,
        description: str,
        topic_key: str = "",
    ) -> str:
        """Generate an image for a topic not in the cache. Takes 3-10 seconds.

        Args:
            description: What the image should depict
            topic_key: If provided, generated image is cached for reuse
        """
        # Send loading state first
        title = f"Generating: {description[:50]}..."
        loading = {
            "type": "generating",
            "description": description,
            "title": title,
        }
        await self._publish_whiteboard(loading)

        # Placeholder — actual image generation is implemented when a
        # provider (e.g. DALL-E, Stability) is configured via AppConfig.
        logger.info(
            "visual_generation_requested",
            description=description[:80],
            topic_key=topic_key,
        )

        # Notify frontend that generation is not yet available so it
        # doesn't remain stuck in spinner/loading state.
        await self._publish_whiteboard({
            "type": "error",
            "message": "Image generation not yet configured",
            "title": title,
        })
        return "Image generation is not yet configured. The whiteboard has been updated."

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _publish_whiteboard(self, payload: dict) -> bool:
        """Publish a whiteboard update to the LiveKit data channel.

        Returns True on success, False on failure.
        """
        room = getattr(self.session, "room", None)
        if room is None:
            logger.warning("whiteboard_publish_skipped", reason="no room")
            return False
        try:
            msg = json.dumps(payload)
            await room.local_participant.publish_data(
                msg.encode(),
                reliable=True,
                topic=_WHITEBOARD_TOPIC,
            )
            logger.info(
                "whiteboard_update",
                type=payload.get("type"),
                title=str(payload.get("title", ""))[:50],
            )
            return True
        except Exception:
            logger.warning("whiteboard_publish_failed", exc_info=True)
            return False

    async def _lookup_visual(self, topic_key: str) -> dict | None:
        """Look up a visual asset from the DB cache."""
        try:
            db_pool = getattr(self.session, "_db_pool", None)
            if db_pool is None:
                logger.debug("visual_lookup_skipped", reason="no db pool")
                return None
            return await get_visual(db_pool, self._subject.value, topic_key)
        except Exception:
            logger.warning(
                "visual_lookup_failed",
                topic_key=topic_key,
                exc_info=True,
            )
            return None
