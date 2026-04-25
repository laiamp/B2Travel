import torch
from PIL.Image import Image as PILImage
from transformers import CLIPModel, CLIPProcessor

MODEL_NAME = "openai/clip-vit-base-patch32"
_processor: CLIPProcessor | None = None
_model: CLIPModel | None = None


def _get_clip_components() -> tuple[CLIPProcessor, CLIPModel]:
    global _processor, _model
    if _processor is None or _model is None:
        _processor = CLIPProcessor.from_pretrained(MODEL_NAME)
        _model = CLIPModel.from_pretrained(MODEL_NAME)
        _model.eval()
    return _processor, _model


def _extract_embedding(raw_output: torch.Tensor, modality: str) -> list[float]:
    embed_attr = "image_embeds" if modality == "image" else "text_embeds"

    if isinstance(raw_output, torch.Tensor):
        tensor = raw_output
    elif hasattr(raw_output, "pooler_output"):
        tensor = raw_output.pooler_output
    elif hasattr(raw_output, embed_attr):
        tensor = getattr(raw_output, embed_attr)
    else:
        raise RuntimeError("Unexpected CLIP output format")

    normalized = tensor / tensor.norm(dim=-1, keepdim=True)
    return normalized[0].cpu().tolist()


def embed_image(pil_image: PILImage) -> list[float]:
    processor, model = _get_clip_components()
    inputs = processor(images=pil_image, return_tensors="pt")

    with torch.no_grad():
        return _extract_embedding(model.get_image_features(**inputs), "image")


def embed_text(text: str) -> list[float]:
    processor, model = _get_clip_components()
    inputs = processor(text=[text], return_tensors="pt", padding=True, truncation=True)

    with torch.no_grad():
        return _extract_embedding(model.get_text_features(**inputs), "text")
