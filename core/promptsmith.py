STYLE_PACKS = {
    "Fantasy": {
        "positive": "fantasy concept art, ornate details, dramatic lighting, epic atmosphere, medieval realism",
        "negative": "modern clothing, guns, cars, text, watermark, blurry, low quality"
    },
    "Cyberpunk": {
        "positive": "cyberpunk, neon lighting, futuristic city, high tech, cinematic shadows, rain, glowing accents",
        "negative": "medieval, rustic, low quality, blurry, watermark, bad anatomy"
    },
    "Creature Design": {
        "positive": "creature design, biological detail, alien anatomy, natural textures, concept art, highly detailed",
        "negative": "cartoon, cute, blurry, low detail, watermark, text"
    },
    "Photorealistic": {
        "positive": "photorealistic, realistic lighting, sharp focus, detailed textures, cinematic photography",
        "negative": "painting, cartoon, anime, low quality, blurry, distorted face, watermark"
    }
}

QUALITY_PACKS = {
    "Fast": "clean composition, clear subject",
    "Balanced": "highly detailed, cinematic lighting, sharp focus, professional composition",
    "Masterpiece": "masterpiece, award-winning, ultra detailed, dramatic composition, volumetric lighting, 8k, sharp focus"
}

DEFAULT_NEGATIVE = "blurry, low quality, watermark, text, deformed, extra limbs, bad anatomy"


def build_prompt(simple_prompt, style="Fantasy", quality="Balanced"):
    style_data = STYLE_PACKS.get(style, STYLE_PACKS["Fantasy"])
    quality_text = QUALITY_PACKS.get(quality, QUALITY_PACKS["Balanced"])

    positive = (
        f"{quality_text}, "
        f"{simple_prompt}, "
        f"{style_data['positive']}"
    )

    negative = f"{DEFAULT_NEGATIVE}, {style_data['negative']}"

    return positive, negative