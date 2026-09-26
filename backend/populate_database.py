from app.database import SessionLocal
from app.models import (
    Color,
    Flower,
    FlowerColor,
    FlowerOccasion,
    FlowerStyle,
    Foliage,
    Occasion,
    Style,
    Wrapping,
)


def populate_database():
    db = SessionLocal()

    try:
        flower_data = [
            (
                "Rose",
                "Classic flower with a romantic and elegant appearance.",
            ),
            (
                "Tulip",
                "Delicate flower with a modern and elegant appearance.",
            ),
            (
                "Hydrangea",
                "Full flower with a soft and elegant appearance.",
            ),
            (
                "Sunflower",
                "Bright and cheerful flower with a rustic appearance.",
            ),
            (
                "Lily",
                "Elegant flower with a classic appearance.",
            ),
            (
                "Carnation",
                "Versatile classic flower available in several colors.",
            ),
            (
                "Daisy",
                "Delicate and cheerful flower with a simple appearance.",
            ),
            (
                "Gerbera",
                "Colorful and cheerful flower with a vibrant appearance.",
            ),
            (
                "Peony",
                "Full and luxurious flower with a romantic appearance.",
            ),
            (
                "Baby's Breath",
                "Delicate small flowers commonly used as a complement in bouquets.",
            ),
        ]

        for name, description in flower_data:
            existing_flower = db.query(Flower).filter_by(name=name).first()

            if existing_flower is None:
                db.add(
                    Flower(
                        name=name,
                        description=description,
                    )
                )

        db.commit()

        color_data = [
            ("Pink", "#FFC0CB"),
            ("Red", "#FF0000"),
            ("White", "#FFFFFF"),
            ("Yellow", "#FFFF00"),
            ("Purple", "#800080"),
            ("Blue", "#0000FF"),
            ("Orange", "#FFA500"),
            ("Green", "#008000"),
        ]

        for name, hex_code in color_data:
            existing_color = db.query(Color).filter_by(name=name).first()

            if existing_color is None:
                db.add(
                    Color(
                        name=name,
                        hex_code=hex_code,
                    )
                )

        db.commit()

        style_data = [
            (
                "Romantic",
                "Soft and expressive style, often associated with roses and delicate flowers.",
            ),
            (
                "Delicate",
                "Light and subtle style featuring soft shapes and small flowers.",
            ),
            (
                "Elegant",
                "Sophisticated style with refined flowers and balanced composition.",
            ),
            (
                "Rustic",
                "Natural and informal style with earthy and organic elements.",
            ),
            (
                "Minimalist",
                "Simple style with a clean composition and few elements.",
            ),
            (
                "Colorful",
                "Vibrant style featuring multiple colors and expressive flowers.",
            ),
            (
                "Classic",
                "Traditional style featuring timeless flowers and compositions.",
            ),
            (
                "Modern",
                "Contemporary style with clean shapes and unconventional combinations.",
            ),
        ]

        for name, description in style_data:
            existing_style = db.query(Style).filter_by(name=name).first()

            if existing_style is None:
                db.add(
                    Style(
                        name=name,
                        description=description,
                    )
                )

        db.commit()

        occasion_data = [
            (
                "Birthday",
                "A celebration of someone's birthday.",
            ),
            (
                "Anniversary",
                "A celebration of a relationship or important milestone.",
            ),
            (
                "Wedding",
                "A celebration associated with weddings and marriage.",
            ),
            (
                "Mother's Day",
                "A celebration honoring mothers and maternal figures.",
            ),
            (
                "Valentine's Day",
                "A celebration associated with romantic relationships and affection.",
            ),
            (
                "Graduation",
                "A celebration of completing an academic or educational milestone.",
            ),
            (
                "Thank You",
                "A thoughtful gesture to express gratitude and appreciation.",
            ),
            (
                "Just Because",
                "A spontaneous gesture without a specific occasion.",
            ),
        ]

        for name, description in occasion_data:
            existing_occasion = db.query(Occasion).filter_by(name=name).first()

            if existing_occasion is None:
                db.add(
                    Occasion(
                        name=name,
                        description=description,
                    )
                )

        db.commit()

        flower_color_data = {
            "Rose": ["Pink", "Red", "White"],
            "Tulip": ["Pink", "White", "Yellow", "Purple"],
            "Hydrangea": ["Blue", "White", "Pink"],
            "Sunflower": ["Yellow"],
            "Lily": ["White", "Pink"],
            "Carnation": ["Pink", "Red", "White"],
            "Daisy": ["White", "Yellow"],
            "Gerbera": ["Pink", "Orange", "Red", "Yellow"],
            "Peony": ["Pink", "White"],
            "Baby's Breath": ["White"],
        }

        for flower_name, color_names in flower_color_data.items():
            flower = db.query(Flower).filter_by(name=flower_name).first()

            if flower is None:
                continue

            for color_name in color_names:
                color = db.query(Color).filter_by(name=color_name).first()

                if color is None:
                    continue

                existing_relationship = (
                    db.query(FlowerColor)
                    .filter_by(
                        flower_id=flower.id,
                        color_id=color.id,
                    )
                    .first()
                )

                if existing_relationship is None:
                    db.add(
                        FlowerColor(
                            flower_id=flower.id,
                            color_id=color.id,
                        )
                    )

        db.commit()

        flower_style_data = {
            "Rose": ["Romantic", "Classic", "Elegant"],
            "Tulip": ["Delicate", "Modern", "Elegant"],
            "Hydrangea": ["Elegant", "Romantic", "Classic"],
            "Sunflower": ["Rustic", "Colorful"],
            "Lily": ["Elegant", "Classic"],
            "Carnation": ["Classic", "Colorful"],
            "Daisy": ["Delicate", "Colorful"],
            "Gerbera": ["Colorful", "Modern"],
            "Peony": ["Romantic", "Elegant"],
            "Baby's Breath": ["Delicate", "Romantic"],
        }

        for flower_name, style_names in flower_style_data.items():
            flower = db.query(Flower).filter_by(name=flower_name).first()

            if flower is None:
                continue

            for style_name in style_names:
                style = db.query(Style).filter_by(name=style_name).first()

                if style is None:
                    continue

                existing_relationship = (
                    db.query(FlowerStyle)
                    .filter_by(
                        flower_id=flower.id,
                        style_id=style.id,
                    )
                    .first()
                )

                if existing_relationship is None:
                    db.add(
                        FlowerStyle(
                            flower_id=flower.id,
                            style_id=style.id,
                        )
                    )

        db.commit()

        flower_occasion_data = {
            "Rose": [
                "Anniversary",
                "Valentine's Day",
                "Mother's Day",
                "Birthday",
                "Just Because",
            ],
            "Tulip": [
                "Birthday",
                "Mother's Day",
                "Thank You",
                "Just Because",
            ],
            "Hydrangea": [
                "Wedding",
                "Mother's Day",
                "Anniversary",
                "Thank You",
            ],
            "Sunflower": [
                "Birthday",
                "Graduation",
                "Thank You",
                "Just Because",
            ],
            "Lily": [
                "Wedding",
                "Mother's Day",
                "Anniversary",
                "Thank You",
            ],
            "Carnation": [
                "Birthday",
                "Mother's Day",
                "Thank You",
                "Just Because",
            ],
            "Daisy": [
                "Birthday",
                "Graduation",
                "Thank You",
                "Just Because",
            ],
            "Gerbera": [
                "Birthday",
                "Graduation",
                "Thank You",
                "Just Because",
            ],
            "Peony": [
                "Wedding",
                "Anniversary",
                "Valentine's Day",
                "Mother's Day",
            ],
            "Baby's Breath": [
                "Wedding",
                "Anniversary",
                "Mother's Day",
                "Just Because",
            ],
        }

        for flower_name, occasion_names in flower_occasion_data.items():
            flower = db.query(Flower).filter_by(name=flower_name).first()

            if flower is None:
                continue

            for occasion_name in occasion_names:
                occasion = db.query(Occasion).filter_by(name=occasion_name).first()

                if occasion is None:
                    continue

                existing_relationship = (
                    db.query(FlowerOccasion)
                    .filter_by(
                        flower_id=flower.id,
                        occasion_id=occasion.id,
                    )
                    .first()
                )

                if existing_relationship is None:
                    db.add(
                        FlowerOccasion(
                            flower_id=flower.id,
                            occasion_id=occasion.id,
                        )
                    )

        db.commit()

        foliage_data = [
            (
                "Eucalyptus",
                "Aromatic foliage with a natural and modern appearance.",
            ),
            (
                "Ruscus",
                "Structured foliage with an elegant and classic appearance.",
            ),
            (
                "Fern",
                "Soft foliage with a rustic and natural appearance.",
            ),
            (
                "Olive Branch",
                "Simple foliage with an elegant and natural appearance.",
            ),
        ]

        for name, description in foliage_data:
            existing_foliage = db.query(Foliage).filter_by(name=name).first()

            if existing_foliage is None:
                db.add(
                    Foliage(
                        name=name,
                        description=description,
                    )
                )

        db.commit()

        wrapping_data = [
            (
                "Kraft Paper",
                "Natural paper wrapping with a rustic appearance.",
            ),
            (
                "White Paper",
                "Clean and versatile paper wrapping.",
            ),
            (
                "Pink Paper",
                "Soft-colored paper wrapping suitable for romantic and delicate bouquets.",
            ),
            (
                "Premium Fabric",
                "Sophisticated fabric wrapping for premium bouquets.",
            ),
        ]

        for name, description in wrapping_data:
            existing_wrapping = db.query(Wrapping).filter_by(name=name).first()

            if existing_wrapping is None:
                db.add(
                    Wrapping(
                        name=name,
                        description=description,
                    )
                )

        db.commit()

        print(
            "Flowers, colors, styles, occasions, foliage, wrappings, "
            "and all relationships added successfully."
        )

    finally:
        db.close()


if __name__ == "__main__":
    populate_database()