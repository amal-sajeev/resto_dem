"""
Extensive seed data: restaurants and menu items with real food image URLs (Unsplash, Pexels).
Run after init_db: python -m scripts.seed
To re-seed, drop tables and run init_db again, then run this script.
"""


import asyncio
import sys
from decimal import Decimal
from datetime import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


from sqlalchemy import select

from app.database import async_session_maker
from app.models import MenuItem, MenuItemOption, Restaurant, Room

# Unsplash CDN URLs (w=600 for consistent size). All free to use.
IMAGES = {
    "restaurant_main": "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=600&q=80",
    "restaurant_sushi": "https://media.istockphoto.com/id/1053855542/photo/chopstick-with-nigiri-sushi-piece.jpg?s=612x612&w=0&k=20&c=sy31QLUoIhuuacPrd9_Aick4D_yVEZEbVTZv_k4tuZc=",
    "restaurant_pool": "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=600&q=80",
    "restaurant_rooftop": "https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=600&q=80",
    "restaurant_breakfast": "https://images.unsplash.com/photo-1551218808-94e220e084d2?w=600&q=80",
    "restaurant_steak": "https://images.unsplash.com/photo-1558030006-450675393462?w=600&q=80",
    "restaurant_lobby": "https://images.unsplash.com/photo-1564501049412-61c2a3083791?w=600&q=80",
    "caesar_salad": "https://images.unsplash.com/photo-1546793665-c74683f339c1?w=600&q=80",
    "grilled_salmon": "https://images.unsplash.com/photo-1467003909585-2f8a72700288?w=600&q=80",
    "chocolate_cake": "https://images.unsplash.com/photo-1578985545062-69928b1d9587?w=600&q=80",
    "sparkling_water": "https://images.unsplash.com/photo-1548839140-29a749e1cf4d?w=600&q=80",
    "edamame": "https://images.pexels.com/photos/28460867/pexels-photo-28460867.jpeg?auto=compress&cs=tinysrgb&w=600",
    "sushi_nigiri": "https://images.pexels.com/photos/271715/pexels-photo-271715.jpeg?auto=compress&cs=tinysrgb&w=600",
    "miso_soup": "https://images.unsplash.com/photo-1547592166-23ac45744acd?w=600&q=80",
    "green_tea": "https://images.unsplash.com/photo-1544787219-7f47ccb76574?w=600&q=80",
    "club_sandwich": "https://images.pexels.com/photos/19202827/pexels-photo-19202827.jpeg?auto=compress&cs=tinysrgb&w=600",
    "fruit_salad": "https://images.unsplash.com/photo-1546548970-71785318a17b?w=600&q=80",
    "lemonade": "https://images.unsplash.com/photo-1621263764928-df1444c5e859?w=600&q=80",
    "soup": "https://images.unsplash.com/photo-1547592166-23ac45744acd?w=600&q=80",
    "pasta": "https://images.pexels.com/photos/64208/pexels-photo-64208.jpeg?auto=compress&cs=tinysrgb&w=600",
    "burger": "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=600&q=80",
    "steak": "https://images.unsplash.com/photo-1558030006-450675393462?w=600&q=80",
    "pizza": "https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?w=600&q=80",
    "ice_cream": "https://images.pexels.com/photos/14132776/pexels-photo-14132776.jpeg?auto=compress&cs=tinysrgb&w=600",
    "tiramisu": "https://images.unsplash.com/photo-1571877227200-a0d98ea607e9?w=600&q=80",
    "wine": "https://images.unsplash.com/photo-1510812431401-41d2bd2722f3?w=600&q=80",
    "coffee": "https://images.unsplash.com/photo-1509042239860-f550ce710b93?w=600&q=80",
    "croissant": "https://images.unsplash.com/photo-1555507036-ab1f4038808a?w=600&q=80",
    "pancakes": "https://images.unsplash.com/photo-1567620905732-2d1ec7ab7445?w=600&q=80",
    "eggs_benedict": "https://images.pexels.com/photos/5914412/pexels-photo-5914412.jpeg?auto=compress&cs=tinysrgb&w=600",
    "smoothie": "https://images.pexels.com/photos/775032/pexels-photo-775032.jpeg?auto=compress&cs=tinysrgb&w=600",
    "tacos": "https://images.unsplash.com/photo-1551504734-5ee1c4a1479b?w=600&q=80",
    "ramen": "https://images.pexels.com/photos/5531482/pexels-photo-5531482.jpeg?auto=compress&cs=tinysrgb&w=600",
    "tempura": "https://images.unsplash.com/photo-1603133872878-684f208fb84b?w=600&q=80",
    "cocktail": "https://images.unsplash.com/photo-1514362545857-3bc16c4c7d1b?w=600&q=80",
    "fish_chips": "https://images.unsplash.com/photo-1579208575657-c595a05383b7?w=600&q=80",
    "cheesecake": "https://media.istockphoto.com/id/1167344045/photo/cheesecake-slice-new-york-style-classical-cheese-cake.jpg?s=612x612&w=0&k=20&c=y3eh7cFEefAYxB_5Ow2n1OJZML_PqFOdnB5Z9nvXdgw=",
    "cappuccino": "https://images.unsplash.com/photo-1572442388796-11668a67e53d?w=600&q=80",
    "juice": "https://images.unsplash.com/photo-1600271886742-f049cd451bba?w=600&q=80",
    "salad_green": "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=600&q=80",
    "risotto": "https://images.unsplash.com/photo-1476124369491-e7addf5db371?w=600&q=80",
    "lobster": "https://images.unsplash.com/photo-1558036117-15d82a90b9b1?w=600&q=80",
    "sashimi": "https://images.unsplash.com/photo-1579584425555-c3ce17fd4351?w=600&q=80",
    "maki": "https://images.unsplash.com/photo-1617196034796-73dfa7b1fd56?w=600&q=80",
    "udon": "https://images.unsplash.com/photo-1583623025817-d180a2221d0a?w=600&q=80",
    "matcha": "https://images.pexels.com/photos/5168518/pexels-photo-5168518.jpeg?auto=compress&cs=tinysrgb&w=600",
    "sake": "https://images.unsplash.com/photo-1569529465841-dfecdab7503b?w=600&q=80",
    "wings": "https://images.pexels.com/photos/11299734/pexels-photo-11299734.jpeg?auto=compress&cs=tinysrgb&w=600",
    "nachos": "https://images.pexels.com/photos/1108775/pexels-photo-1108775.jpeg?auto=compress&cs=tinysrgb&w=600",
    "caprese": "https://images.pexels.com/photos/29935505/pexels-photo-29935505.jpeg?auto=compress&cs=tinysrgb&w=600",
    "bruschetta": "https://images.unsplash.com/photo-1572695157366-5e585ab2b69f?w=600&q=80",
    "crab_cake": "https://images.unsplash.com/photo-1559847844-5315695dadae?w=600&q=80",
    "lamb": "https://images.unsplash.com/photo-1544025162-d76694265947?w=600&q=80",
    "seabass": "https://images.unsplash.com/photo-1467003909585-2f8a72700288?w=600&q=80",
    "vegan_bowl": "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=600&q=80",
    "creme_brulee": "https://images.unsplash.com/photo-1470124182917-cc6e71b22ecc?w=600&q=80",
    "panna_cotta": "https://images.unsplash.com/photo-1488477181946-6428a0291777?w=600&q=80",
    "beer": "https://images.unsplash.com/photo-1535958636474-b021ee887b13?w=600&q=80",
    "mojito": "https://images.unsplash.com/photo-1551538827-9c037cb4f32a?w=600&q=80",
}


def _img(key: str) -> str:
    return IMAGES.get(key, IMAGES["restaurant_main"])


async def seed() -> None:
    async with async_session_maker() as session:
        existing = await session.execute(select(Restaurant).limit(1))
        if existing.scalar_one_or_none() is not None:
            print("Data already present. Delete existing data first (e.g. drop tables and run init_db) to re-seed.")
            return

        # Seed rooms (101-110, 201-210, 301-310, 401-410)
        for floor in (1, 2, 3, 4):
            for n in range(1, 11):
                room_num = f"{floor}{n:02d}"  # 101..110, 201..210, 301..310, 401..410
                session.add(Room(room_number=room_num, display_name=f"Room {room_num}"))
        await session.flush()

        restaurants = [
            Restaurant(
                name="Main Restaurant",
                description="All-day dining with international cuisine. From hearty breakfasts to refined dinners, our main restaurant offers a wide selection of dishes in an elegant setting.",
                image_url=IMAGES["restaurant_main"],
                open_from=time(7, 0),
                open_until=time(22, 0),
            ),
            Restaurant(
                name="Sushi Bar",
                description="Fresh sushi and authentic Japanese cuisine. Our chefs prepare nigiri, maki, and sashimi daily with the finest ingredients.",
                image_url=IMAGES["restaurant_sushi"],
                open_from=time(11, 30),
                open_until=time(22, 0),
            ),
            Restaurant(
                name="Pool Grill",
                description="Light bites and refreshing drinks by the pool. Perfect for a casual lunch or sunset cocktails.",
                image_url=IMAGES["restaurant_pool"],
                open_from=time(10, 0),
                open_until=time(18, 0),
            ),
            Restaurant(
                name="Rooftop Lounge",
                description="Stunning views and a sophisticated menu. Small plates, premium cocktails, and live music on select evenings.",
                image_url=IMAGES["restaurant_rooftop"],
                open_from=time(16, 0),
                open_until=time(23, 30),
            ),
            Restaurant(
                name="Breakfast & Co",
                description="Start your day right. Full breakfast buffet, à la carte eggs, pastries, and specialty coffee until 11:00.",
                image_url=IMAGES["restaurant_breakfast"],
                open_from=time(6, 0),
                open_until=time(11, 0),
            ),
            Restaurant(
                name="The Steakhouse",
                description="Prime cuts, dry-aged beef, and classic sides. A destination for meat lovers with an extensive wine list.",
                image_url=IMAGES["restaurant_steak"],
                open_from=time(18, 0),
                open_until=time(22, 30),
            ),
            Restaurant(
                name="Lobby Bar",
                description="All-day snacks and drinks in the heart of the hotel. Quick bites, coffee, and cocktails in a relaxed atmosphere.",
                image_url=IMAGES["restaurant_lobby"],
                open_from=time(6, 0),
                open_until=time(23, 0),
            ),
        ]
        for r in restaurants:
            session.add(r)
        await session.flush()

        def mi(restaurant, name, description, price, category, image_key=None, allergens=None, requires_option_selection=False):
            return MenuItem(
                restaurant_id=restaurant.id,
                name=name,
                description=description,
                price=Decimal(price),
                category=category,
                image_url=_img(image_key or "restaurant_main"),
                allergens=allergens,
                requires_option_selection=requires_option_selection,
            )

        items = []

        # ----- Main Restaurant -----
        r1 = restaurants[0]
        items += [
            mi(r1, "Caesar Salad", "Crisp romaine, parmesan, house croutons, classic Caesar dressing", "14.00", "Starters", "caesar_salad", "Dairy, Gluten"),
            mi(r1, "Caprese Salad", "Buffalo mozzarella, heirloom tomatoes, basil, balsamic glaze", "13.00", "Starters", "caprese", "Dairy"),
            mi(r1, "Bruschetta", "Toasted ciabatta with tomato, garlic, basil and olive oil", "10.00", "Starters", "bruschetta", "Gluten"),
            mi(r1, "Soup of the Day", "Chef's daily selection, served with bread", "9.00", "Starters", "soup"),
            mi(r1, "Grilled Salmon", "Atlantic salmon, seasonal vegetables, lemon butter sauce", "28.00", "Mains", "grilled_salmon", "Fish"),
            mi(r1, "Pasta Primavera", "Fresh pasta, seasonal vegetables, garlic, parmesan", "22.00", "Mains", "pasta", "Gluten, Dairy"),
            mi(r1, "Classic Burger", "Angus beef, lettuce, tomato, pickles, fries", "19.00", "Mains", "burger"),
            mi(r1, "Ribeye Steak", "12oz ribeye, mashed potatoes, green beans, peppercorn sauce", "38.00", "Mains", "steak"),
            mi(r1, "Margherita Pizza", "San Marzano tomato, mozzarella, fresh basil", "18.00", "Mains", "pizza", "Gluten, Dairy"),
            mi(r1, "Vegetable Risotto", "Arborio rice, seasonal vegetables, parmesan, white wine", "22.00", "Mains", "risotto", "Dairy"),
            mi(r1, "Chocolate Cake", "Rich dark chocolate layer cake, chocolate ganache", "11.00", "Desserts", "chocolate_cake", "Gluten, Dairy, Eggs"),
            mi(r1, "Tiramisu", "Espresso-soaked ladyfingers, mascarpone, cocoa", "12.00", "Desserts", "tiramisu", "Dairy, Eggs, Gluten"),
            mi(r1, "Crème Brûlée", "Classic vanilla custard with caramelized sugar", "11.00", "Desserts", "creme_brulee", "Dairy, Eggs"),
            mi(r1, "Ice Cream (3 scoops)", "Choice of vanilla, chocolate, strawberry", "9.00", "Desserts", "ice_cream", "Dairy", True),
            mi(r1, "Sparkling Water", "500ml bottle", "5.00", "Drinks", "sparkling_water"),
            mi(r1, "House Wine", "Glass of red or white", "10.00", "Drinks", "wine", None, True),
            mi(r1, "Espresso", "Single or double", "4.00", "Drinks", "coffee"),
            mi(r1, "Fresh Orange Juice", "250ml", "6.00", "Drinks", "juice", None, True),
        ]

        # ----- Sushi Bar -----
        r2 = restaurants[1]
        items += [
            mi(r2, "Edamame", "Steamed soybeans with sea salt", "7.00", "Starters", "edamame", "Soy"),
            mi(r2, "Miso Soup", "Traditional miso with tofu, seaweed, scallions", "6.00", "Starters", "miso_soup", "Soy"),
            mi(r2, "Seaweed Salad", "Wakame with sesame dressing", "8.00", "Starters", "salad_green"),
            mi(r2, "Salmon Nigiri (4 pcs)", "Fresh salmon over seasoned rice", "16.00", "Mains", "sushi_nigiri", "Fish"),
            mi(r2, "Tuna Sashimi (6 pcs)", "Premium bluefin tuna", "20.00", "Mains", "sashimi", "Fish"),
            mi(r2, "California Roll (8 pcs)", "Crab, avocado, cucumber", "14.00", "Mains", "maki", "Fish, Shellfish"),
            mi(r2, "Dragon Roll (8 pcs)", "Eel, cucumber, avocado, eel sauce", "18.00", "Mains", "maki", "Fish"),
            mi(r2, "Tempura Udon", "Crispy tempura, thick udon noodles, dashi broth", "16.00", "Mains", "udon", "Gluten"),
            mi(r2, "Ramen", "Rich pork broth, chashu, egg, nori, scallions", "16.00", "Mains", "ramen", "Gluten, Eggs"),
            mi(r2, "Vegetable Tempura", "Seasonal vegetables, light batter, tentsuyu", "12.00", "Mains", "tempura", "Gluten"),
            mi(r2, "Green Tea", "Hot or iced", "4.00", "Drinks", "green_tea", None, True),
            mi(r2, "Matcha Latte", "Ceremonial matcha with milk of choice", "7.00", "Drinks", "matcha", "Dairy"),
            mi(r2, "Sake (180ml)", "House sake, cold or warm", "12.00", "Drinks", "sake", None, True),
        ]

        # ----- Pool Grill -----
        r3 = restaurants[2]
        items += [
            mi(r3, "Fruit Salad", "Seasonal fruits with mint and honey", "9.00", "Starters", "fruit_salad"),
            mi(r3, "Nachos", "Tortilla chips, cheese, jalapeños, sour cream, guacamole", "12.00", "Starters", "nachos", "Dairy"),
            mi(r3, "Chicken Wings", "Crispy wings, choice of buffalo or BBQ, celery and blue cheese", "13.00", "Starters", "wings", None, True),
            mi(r3, "Club Sandwich", "Chicken, bacon, lettuce, tomato, mayo, fries", "15.00", "Mains", "club_sandwich"),
            mi(r3, "Fish & Chips", "Beer-battered cod, tartar sauce, fries", "18.00", "Mains", "fish_chips", "Fish, Gluten"),
            mi(r3, "Grilled Chicken Wrap", "Lettuce, tomato, avocado, chipotle mayo", "14.00", "Mains", "club_sandwich"),
            mi(r3, "Iced Lemonade", "Fresh squeezed, 400ml", "6.00", "Drinks", "lemonade"),
            mi(r3, "Smoothie", "Strawberry, mango, or mixed berry", "8.00", "Drinks", "smoothie", "Dairy", True),
            mi(r3, "Cocktail of the Day", "Ask your server", "14.00", "Drinks", "cocktail"),
            mi(r3, "Mojito", "White rum, mint, lime, soda", "12.00", "Drinks", "mojito"),
            mi(r3, "Local Beer", "Draft or bottle", "7.00", "Drinks", "beer", "Gluten", True),
        ]

        # ----- Rooftop Lounge -----
        r4 = restaurants[3]
        items += [
            mi(r4, "Tuna Tartare", "Fresh tuna, avocado, sesame, wonton crisps", "18.00", "Starters", "sashimi", "Fish"),
            mi(r4, "Crab Cakes", "Two cakes, remoulade, lemon", "16.00", "Starters", "crab_cake", "Shellfish"),
            mi(r4, "Tacos (3 pcs)", "Choice of fish, chicken, or cauliflower", "14.00", "Mains", "tacos", None, True),
            mi(r4, "Lobster Roll", "Buttered brioche, fresh lobster, herbs", "32.00", "Mains", "lobster", "Shellfish"),
            mi(r4, "Beef Sliders", "Three sliders, caramelized onion, aioli", "15.00", "Mains", "burger"),
            mi(r4, "Cheesecake", "New York style, berry compote", "11.00", "Desserts", "cheesecake", "Dairy, Gluten"),
            mi(r4, "Panna Cotta", "Vanilla panna cotta, seasonal fruit", "10.00", "Desserts", "panna_cotta", "Dairy"),
            mi(r4, "Signature Cocktail", "Bartender's choice", "16.00", "Drinks", "cocktail"),
            mi(r4, "Champagne Glass", "House champagne", "18.00", "Drinks", "wine"),
        ]

        # ----- Breakfast & Co -----
        r5 = restaurants[4]
        items += [
            mi(r5, "Croissant", "Butter croissant, jam and butter", "5.00", "Starters", "croissant", "Gluten, Dairy"),
            mi(r5, "Fresh Fruit Plate", "Seasonal selection", "10.00", "Starters", "fruit_salad"),
            mi(r5, "Pancakes", "Stack of three, maple syrup, butter", "14.00", "Mains", "pancakes", "Gluten, Dairy"),
            mi(r5, "Eggs Benedict", "Poached eggs, English muffin, hollandaise, side salad", "16.00", "Mains", "eggs_benedict", "Eggs, Dairy"),
            mi(r5, "Avocado Toast", "Sourdough, smashed avocado, poached egg, chili flakes", "14.00", "Mains", "bruschetta", "Gluten, Eggs"),
            mi(r5, "Full English", "Eggs, bacon, sausage, beans, tomato, toast", "18.00", "Mains", "eggs_benedict"),
            mi(r5, "Omelette", "Three eggs, choice of fillings", "15.00", "Mains", "eggs_benedict", "Eggs, Dairy", True),
            mi(r5, "Acai Bowl", "Acai, granola, banana, berries, honey", "12.00", "Mains", "smoothie"),
            mi(r5, "Espresso", "Single or double", "4.00", "Drinks", "coffee"),
            mi(r5, "Cappuccino", "Single or double shot", "5.00", "Drinks", "cappuccino", "Dairy"),
            mi(r5, "Fresh Juice", "Orange, apple, or carrot", "6.00", "Drinks", "juice", None, True),
            mi(r5, "Smoothie", "Berry, green, or tropical", "8.00", "Drinks", "smoothie", None, True),
        ]

        # ----- The Steakhouse -----
        r6 = restaurants[5]
        items += [
            mi(r6, "Caesar Salad", "Classic Caesar with anchovy dressing", "14.00", "Starters", "caesar_salad", "Dairy, Gluten"),
            mi(r6, "French Onion Soup", "Caramelized onions, gruyère, crouton", "11.00", "Starters", "soup", "Dairy, Gluten"),
            mi(r6, "Ribeye 12oz", "Prime ribeye, mashed potato, seasonal vegetables", "45.00", "Mains", "steak"),
            mi(r6, "Filet Mignon 8oz", "Beef fillet, peppercorn or béarnaise, sides", "52.00", "Mains", "steak", None, True),
            mi(r6, "Grilled Lamb Chops", "Three chops, mint jus, roasted potatoes", "40.00", "Mains", "lamb"),
            mi(r6, "Grilled Sea Bass", "Whole fish, herbs, lemon, vegetables", "34.00", "Mains", "seabass", "Fish"),
            mi(r6, "Surf & Turf", "6oz fillet, lobster tail, drawn butter", "62.00", "Mains", "lobster"),
            mi(r6, "Mashed Potatoes", "Side", "7.00", "Sides", "steak"),
            mi(r6, "Creamed Spinach", "Side", "7.00", "Sides", "salad_green"),
            mi(r6, "Chocolate Lava Cake", "Warm cake, molten center, vanilla ice cream", "13.00", "Desserts", "chocolate_cake", "Gluten, Dairy"),
            mi(r6, "Cheesecake", "New York style", "11.00", "Desserts", "cheesecake", "Dairy"),
            mi(r6, "Red Wine", "Glass", "14.00", "Drinks", "wine"),
            mi(r6, "Red Wine Bottle", "House selection", "48.00", "Drinks", "wine"),
        ]

        # ----- Lobby Bar -----
        r7 = restaurants[6]
        items += [
            mi(r7, "Mixed Nuts", "Roasted, salted", "6.00", "Snacks", "fruit_salad"),
            mi(r7, "Olives", "Marinated olives", "7.00", "Snacks", "caprese"),
            mi(r7, "Club Sandwich", "Chicken, bacon, lettuce, tomato, fries", "15.00", "Mains", "club_sandwich"),
            mi(r7, "Caesar Salad", "Half portion", "9.00", "Mains", "caesar_salad", "Dairy"),
            mi(r7, "Espresso", "Single or double", "4.00", "Drinks", "coffee"),
            mi(r7, "Cappuccino", "Single or double", "5.00", "Drinks", "cappuccino", "Dairy"),
            mi(r7, "Fresh Juice", "Orange or apple", "6.00", "Drinks", "juice", None, True),
            mi(r7, "Sparkling Water", "500ml", "5.00", "Drinks", "sparkling_water"),
            mi(r7, "House Wine", "Red or white glass", "10.00", "Drinks", "wine", None, True),
            mi(r7, "Cocktail", "Classic or signature", "14.00", "Drinks", "cocktail"),
        ]

        for m in items:
            session.add(m)
        await session.flush()

        # Add options for items that support add-ons (priced)
        for rest in [r1, r5, r7]:
            r = await session.execute(select(MenuItem).where(MenuItem.restaurant_id == rest.id, MenuItem.name == "Espresso"))
            mi = r.scalar_one_or_none()
            if mi:
                session.add(MenuItemOption(menu_item_id=mi.id, label="Double shot", price_delta=Decimal("1.50")))
        for rest in [r5, r7]:
            r = await session.execute(select(MenuItem).where(MenuItem.restaurant_id == rest.id, MenuItem.name == "Cappuccino"))
            mi = r.scalar_one_or_none()
            if mi:
                session.add(MenuItemOption(menu_item_id=mi.id, label="Double shot", price_delta=Decimal("1.50")))
                session.add(MenuItemOption(menu_item_id=mi.id, label="Extra shot", price_delta=Decimal("1.00")))
        r = await session.execute(select(MenuItem).where(MenuItem.restaurant_id == r1.id, MenuItem.name == "Margherita Pizza"))
        pizza = r.scalar_one_or_none()
        if pizza:
            for label, delta in [("Pepperoni", "2.00"), ("Mushrooms", "1.00"), ("Olives", "1.00"), ("Extra cheese", "1.50"), ("Jalapeños", "1.00")]:
                session.add(MenuItemOption(menu_item_id=pizza.id, label=label, price_delta=Decimal(delta)))

        # r1: Classic Burger add-ons
        r = await session.execute(select(MenuItem).where(MenuItem.restaurant_id == r1.id, MenuItem.name == "Classic Burger"))
        burger = r.scalar_one_or_none()
        if burger:
            for label, delta in [("Extra patty", "3.00"), ("Cheese", "1.50"), ("Bacon", "2.00")]:
                session.add(MenuItemOption(menu_item_id=burger.id, label=label, price_delta=Decimal(delta)))

        # r2 Sushi Bar: Ramen and Matcha Latte add-ons
        r = await session.execute(select(MenuItem).where(MenuItem.restaurant_id == r2.id, MenuItem.name == "Ramen"))
        ramen = r.scalar_one_or_none()
        if ramen:
            for label, delta in [("Extra egg", "1.00"), ("Extra chashu", "2.50"), ("Nori", "0.50")]:
                session.add(MenuItemOption(menu_item_id=ramen.id, label=label, price_delta=Decimal(delta)))
        r = await session.execute(select(MenuItem).where(MenuItem.restaurant_id == r2.id, MenuItem.name == "Matcha Latte"))
        matcha = r.scalar_one_or_none()
        if matcha:
            for label, delta in [("Oat milk", "0.50"), ("Extra shot", "1.00")]:
                session.add(MenuItemOption(menu_item_id=matcha.id, label=label, price_delta=Decimal(delta)))

        # r3 Pool Grill: Chicken Wings (required choice: sauce) and Mojito add-ons
        r = await session.execute(select(MenuItem).where(MenuItem.restaurant_id == r3.id, MenuItem.name == "Chicken Wings"))
        wings = r.scalar_one_or_none()
        if wings:
            for label, delta in [("Buffalo", "0"), ("BBQ", "0")]:
                session.add(MenuItemOption(menu_item_id=wings.id, label=label, price_delta=Decimal(delta)))
        r = await session.execute(select(MenuItem).where(MenuItem.restaurant_id == r3.id, MenuItem.name == "Mojito"))
        mojito = r.scalar_one_or_none()
        if mojito:
            session.add(MenuItemOption(menu_item_id=mojito.id, label="Premium rum", price_delta=Decimal("2.00")))

        # r4 Rooftop: Tacos (required choice: filling) and Signature Cocktail add-ons
        r = await session.execute(select(MenuItem).where(MenuItem.restaurant_id == r4.id, MenuItem.name == "Tacos (3 pcs)"))
        tacos = r.scalar_one_or_none()
        if tacos:
            for label, delta in [("Fish", "0"), ("Chicken", "0"), ("Cauliflower", "0")]:
                session.add(MenuItemOption(menu_item_id=tacos.id, label=label, price_delta=Decimal(delta)))
        r = await session.execute(select(MenuItem).where(MenuItem.restaurant_id == r4.id, MenuItem.name == "Signature Cocktail"))
        sig_cocktail = r.scalar_one_or_none()
        if sig_cocktail:
            session.add(MenuItemOption(menu_item_id=sig_cocktail.id, label="Premium spirit", price_delta=Decimal("3.00")))

        # r5 Breakfast: Pancakes add-ons; Omelette (required choice: fillings)
        r = await session.execute(select(MenuItem).where(MenuItem.restaurant_id == r5.id, MenuItem.name == "Pancakes"))
        pancakes = r.scalar_one_or_none()
        if pancakes:
            for label, delta in [("Extra berries", "1.50"), ("Nutella", "1.00")]:
                session.add(MenuItemOption(menu_item_id=pancakes.id, label=label, price_delta=Decimal(delta)))
        r = await session.execute(select(MenuItem).where(MenuItem.restaurant_id == r5.id, MenuItem.name == "Omelette"))
        omelette = r.scalar_one_or_none()
        if omelette:
            for label, delta in [("Cheese", "0"), ("Mushrooms", "0"), ("Ham", "0"), ("Veggie", "0")]:
                session.add(MenuItemOption(menu_item_id=omelette.id, label=label, price_delta=Decimal(delta)))

        # r6 Steakhouse: Ribeye 12oz and Red Wine add-ons
        r = await session.execute(select(MenuItem).where(MenuItem.restaurant_id == r6.id, MenuItem.name == "Ribeye 12oz"))
        ribeye = r.scalar_one_or_none()
        if ribeye:
            for label, delta in [("Béarnaise sauce", "1.50"), ("Truffle butter", "3.00")]:
                session.add(MenuItemOption(menu_item_id=ribeye.id, label=label, price_delta=Decimal(delta)))
        r = await session.execute(select(MenuItem).where(MenuItem.restaurant_id == r6.id, MenuItem.name == "Red Wine"))
        red_wine = r.scalar_one_or_none()
        if red_wine:
            session.add(MenuItemOption(menu_item_id=red_wine.id, label="Large pour", price_delta=Decimal("4.00")))

        # r7 Lobby Bar: Club Sandwich and Cocktail add-ons (Espresso/Cappuccino already have options)
        r = await session.execute(select(MenuItem).where(MenuItem.restaurant_id == r7.id, MenuItem.name == "Club Sandwich"))
        club = r.scalar_one_or_none()
        if club:
            session.add(MenuItemOption(menu_item_id=club.id, label="Add avocado", price_delta=Decimal("1.50")))
        r = await session.execute(select(MenuItem).where(MenuItem.restaurant_id == r7.id, MenuItem.name == "Cocktail"))
        lobby_cocktail = r.scalar_one_or_none()
        if lobby_cocktail:
            session.add(MenuItemOption(menu_item_id=lobby_cocktail.id, label="Premium spirit", price_delta=Decimal("3.00")))

        # Juice items (requires_option_selection): choice of flavor
        for rest, juice_name in [(r1, "Fresh Orange Juice"), (r5, "Fresh Juice")]:
            r = await session.execute(select(MenuItem).where(MenuItem.restaurant_id == rest.id, MenuItem.name == juice_name))
            juice = r.scalar_one_or_none()
            if juice:
                for label, delta in [("Orange", "0"), ("Apple", "0"), ("Carrot", "0.50")]:
                    session.add(MenuItemOption(menu_item_id=juice.id, label=label, price_delta=Decimal(delta)))
        r = await session.execute(select(MenuItem).where(MenuItem.restaurant_id == r7.id, MenuItem.name == "Fresh Juice"))
        juice7 = r.scalar_one_or_none()
        if juice7:
            for label, delta in [("Orange", "0"), ("Apple", "0")]:
                session.add(MenuItemOption(menu_item_id=juice7.id, label=label, price_delta=Decimal(delta)))

        # r1: Ice Cream and House Wine (required choice)
        r = await session.execute(select(MenuItem).where(MenuItem.restaurant_id == r1.id, MenuItem.name == "Ice Cream (3 scoops)"))
        ice_cream = r.scalar_one_or_none()
        if ice_cream:
            for label, delta in [("Vanilla", "0"), ("Chocolate", "0"), ("Strawberry", "0")]:
                session.add(MenuItemOption(menu_item_id=ice_cream.id, label=label, price_delta=Decimal(delta)))
        r = await session.execute(select(MenuItem).where(MenuItem.restaurant_id == r1.id, MenuItem.name == "House Wine"))
        house_wine_r1 = r.scalar_one_or_none()
        if house_wine_r1:
            for label, delta in [("Red", "0"), ("White", "0")]:
                session.add(MenuItemOption(menu_item_id=house_wine_r1.id, label=label, price_delta=Decimal(delta)))

        # r2: Green Tea and Sake (required choice)
        r = await session.execute(select(MenuItem).where(MenuItem.restaurant_id == r2.id, MenuItem.name == "Green Tea"))
        green_tea = r.scalar_one_or_none()
        if green_tea:
            for label, delta in [("Hot", "0"), ("Iced", "0")]:
                session.add(MenuItemOption(menu_item_id=green_tea.id, label=label, price_delta=Decimal(delta)))
        r = await session.execute(select(MenuItem).where(MenuItem.restaurant_id == r2.id, MenuItem.name == "Sake (180ml)"))
        sake = r.scalar_one_or_none()
        if sake:
            for label, delta in [("Cold", "0"), ("Warm", "0")]:
                session.add(MenuItemOption(menu_item_id=sake.id, label=label, price_delta=Decimal(delta)))

        # r3: Smoothie and Local Beer (required choice)
        r = await session.execute(select(MenuItem).where(MenuItem.restaurant_id == r3.id, MenuItem.name == "Smoothie"))
        smoothie_r3 = r.scalar_one_or_none()
        if smoothie_r3:
            for label, delta in [("Strawberry", "0"), ("Mango", "0"), ("Mixed berry", "0")]:
                session.add(MenuItemOption(menu_item_id=smoothie_r3.id, label=label, price_delta=Decimal(delta)))
        r = await session.execute(select(MenuItem).where(MenuItem.restaurant_id == r3.id, MenuItem.name == "Local Beer"))
        local_beer = r.scalar_one_or_none()
        if local_beer:
            for label, delta in [("Draft", "0"), ("Bottle", "0")]:
                session.add(MenuItemOption(menu_item_id=local_beer.id, label=label, price_delta=Decimal(delta)))

        # r5: Smoothie (required choice)
        r = await session.execute(select(MenuItem).where(MenuItem.restaurant_id == r5.id, MenuItem.name == "Smoothie"))
        smoothie_r5 = r.scalar_one_or_none()
        if smoothie_r5:
            for label, delta in [("Berry", "0"), ("Green", "0"), ("Tropical", "0")]:
                session.add(MenuItemOption(menu_item_id=smoothie_r5.id, label=label, price_delta=Decimal(delta)))

        # r6: Filet Mignon 8oz (required choice: sauce)
        r = await session.execute(select(MenuItem).where(MenuItem.restaurant_id == r6.id, MenuItem.name == "Filet Mignon 8oz"))
        filet = r.scalar_one_or_none()
        if filet:
            for label, delta in [("Peppercorn", "0"), ("Béarnaise", "1.50")]:
                session.add(MenuItemOption(menu_item_id=filet.id, label=label, price_delta=Decimal(delta)))

        # r7: House Wine (required choice)
        r = await session.execute(select(MenuItem).where(MenuItem.restaurant_id == r7.id, MenuItem.name == "House Wine"))
        house_wine_r7 = r.scalar_one_or_none()
        if house_wine_r7:
            for label, delta in [("Red", "0"), ("White", "0")]:
                session.add(MenuItemOption(menu_item_id=house_wine_r7.id, label=label, price_delta=Decimal(delta)))

        await session.commit()
        print(f"Seed completed: 40 rooms, {len(restaurants)} restaurants, {len(items)} menu items.")


if __name__ == "__main__":
    asyncio.run(seed())
