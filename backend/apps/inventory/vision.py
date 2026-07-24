import base64
import logging
from typing import Literal

from django.conf import settings
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

VISION_MODEL = "claude-sonnet-5"

IDENTIFY_PROMPT = (
    "Identify the toy in this photo for a library inventory intake form. "
    "Provide its product/model name, manufacturer, visible physical condition, "
    "and manufacturer-recommended age rating if shown on packaging or the item itself. "
    "If a field isn't determinable from the photo, make your best reasonable guess for "
    "model_name/make, leave age_rating_label blank, and default condition to LIGHTLY_USED."
)


class ToyIdentification(BaseModel):
    model_name: str = Field(description="The toy's product/model name")
    make: str = Field(description="Manufacturer or brand")
    condition: Literal["NEW", "LIGHTLY_USED", "USED", "DAMAGED"] = Field(
        description="Visible physical condition of the toy"
    )
    age_rating_label: str = Field(
        default="", description="Manufacturer-recommended age range, e.g. '3+', if visible"
    )
    description: str = Field(default="", description="One or two sentence visual description")


def identify_toy_from_image(image_bytes, mime_type="image/jpeg"):
    if not settings.ANTHROPIC_API_KEY:
        raise ValueError("Image identification is not configured (missing ANTHROPIC_API_KEY)")

    model = ChatAnthropic(
        model=VISION_MODEL, max_tokens=1024, api_key=settings.ANTHROPIC_API_KEY
    )
    structured_model = model.with_structured_output(ToyIdentification)

    image_b64 = base64.standard_b64encode(image_bytes).decode("utf-8")
    message = HumanMessage(
        content=[
            {"type": "text", "text": IDENTIFY_PROMPT},
            {
                "type": "image",
                "source_type": "base64",
                "data": image_b64,
                "mime_type": mime_type,
            },
        ]
    )
    try:
        return structured_model.invoke([message])
    except Exception:
        logger.exception("Toy image identification request failed")
        raise
