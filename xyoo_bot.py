import os
import json
import discord
from discord.ext import commands
from discord import app_commands
import datetime
import logging
import asyncio
from quart import Quart, request, jsonify, send_file
from quart_cors import cors

# ================== CONFIGURATION ==================
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
GUILD_ID = int(os.getenv('GUILD_ID', '1129463696737972267'))
ORDER_CHANNEL_ID = int(os.getenv('ORDER_CHANNEL_ID', '0'))
API_KEY = os.getenv('API_SECRET', 'change-me-in-production')
PORT = int(os.getenv('PORT', 8080))
SUPPORT_USER_ID = 592402229978333331
VOUCH_CHANNEL_ID = int(os.getenv('VOUCH_CHANNEL_ID', '0'))

WEBSITE_URL = os.getenv('WEBSITE_URL', 'https://xyooshop.onrender.com/')
YOUR_IMAGE_URL = "https://cdn.discordapp.com/attachments/1124170237089165325/1496726350101217402/standard.gif?ex=6a00af49&is=69ff5dc9&hm=3592503d7e5deeefd83dafb3b8caad324a2e119e1728b040fb9784e00d788718"

EMBED_COLOR = discord.Color.from_rgb(186, 85, 211)
GOLD_COLOR = discord.Color.gold()
GREEN_COLOR = discord.Color.green()
RED_COLOR = discord.Color.red()

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

app = Quart(__name__, static_folder='static', static_url_path='/static')
app = cors(app, allow_origin="*")

CONFIG_FILE = "bot_config.json"

# ---------- Default full product list ----------
DEFAULT_PRODUCTS = [
    {"id": 1,  "name": "5x Dragon's Breath Seed",  "image": "dbreath.png", "price": 11.99, "category": "Seed"},
    {"id": 2,  "name": "10x Dragon's Breath Seed", "image": "dbreath.png", "price": 18.99, "category": "Seed"},
    {"id": 3,  "name": "5x Ghost Pepper Seed",     "image": "gpepper.png", "price": 9.99,  "category": "Seed"},
    {"id": 4,  "name": "10x Ghost Pepper Seed",    "image": "gpepper.png", "price": 16.99, "category": "Seed"},
    {"id": 5,  "name": "50x Rainbow Seed",         "image": "rbseed.png",  "price": 4.99,  "category": "Seed"},
    {"id": 6,  "name": "100x Rainbow Seed",        "image": "rbseed.png",  "price": 8.99,  "category": "Seed"},
    {"id": 7,  "name": "50x Gold Seed",            "image": "gseed.png",   "price": 2.99,  "category": "Seed"},
    {"id": 8,  "name": "100x Gold Seed",           "image": "gseed.png",   "price": 4.99,  "category": "Seed"},
    {"id": 9,  "name": "Moon Blossom",             "image": "mb.png",      "price": 6.99,  "category": "Seed"},
    {"id": 10, "name": "Dragon Fly",               "image": "df.png",      "price": 4.99,  "category": "Pet"},
    {"id": 11, "name": "Unicorn",                  "image": "uni.png",     "price": 5.99,  "category": "Pet"},
    {"id": 12, "name": "Bear",                     "image": "bear.png",    "price": 3.99,  "category": "Pet"},
    {"id": 13, "name": "Ice Serpent",              "image": "is.png",      "price": 27.99, "category": "Pet"},
    {"id": 14, "name": "1M Sheckles",              "image": "sheckles.png","price": 1.99,  "category": "Currency"},
]

def migrate_config(config):
    if "products" not in config:
        if "prices" in config:
            default_map = {p["name"]: p for p in DEFAULT_PRODUCTS}
            new_products = []
            for name, price in config["prices"].items():
                if name in default_map:
                    entry = default_map[name].copy()
                else:
                    entry = {"id": 0, "name": name, "image": "unknown.png", "category": "Unknown"}
                entry["price"] = price
                new_products.append(entry)
            for i, p in enumerate(new_products, start=1):
                p["id"] = i
            config["products"] = new_products
            del config["prices"]
        else:
            config["products"] = DEFAULT_PRODUCTS.copy()
    if "next_id" not in config:
        max_id = max((p["id"] for p in config["products"]), default=0)
        config["next_id"] = max_id + 1
    return config

def load_config():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
                config = migrate_config(config)
                if "user_orders" not in config:
                    config["user_orders"] = {}
                return config
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
    return {"products": DEFAULT_PRODUCTS.copy(), "user_orders": {}, "next_id": len(DEFAULT_PRODUCTS)+1}

def save_config(config):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=4)
        logger.info("Config saved")
    except Exception as e:
        logger.error(f"Failed to save config: {e}")

class XyooBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)
        self.config = load_config()

    async def setup_hook(self):
        self.tree.add_command(ping_command)
        self.tree.add_command(xyoo_command)
        self.tree.add_command(setup_command)
        self.tree.add_command(request_vouch_command)
        self.tree.add_command(close_command)
        self.tree.add_command(setprice_command)
        self.tree.add_command(addproduct_command)
        self.tree.add_command(removeitem_command)

        if os.getenv('SYNC_COMMANDS', 'false').lower() == 'true':
            await self.tree.sync()
            guild = discord.Object(id=GUILD_ID)
            await self.tree.sync(guild=guild)
            logger.info("Commands synced")
        else:
            logger.info("Skipping command sync")

bot = XyooBot()

# ================== EMBED TEMPLATES ==================
def get_main_embed():
    embed = discord.Embed(
        title="🤖 Xyoo Assistant",
        description="▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n✨ **Welcome to Xyoo Shop!** ✨\n▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n\nGet everything you need with just one click!\n👇 **Select an option below to get started:**",
        color=EMBED_COLOR,
        timestamp=datetime.datetime.now()
    )
    embed.add_field(name="📋 Available Options", value="📋 **Instructions How To Order**\n💳 **Payment Methods**\n🛍️ **Order Here**\n💰 **View Prices**", inline=False)
    embed.add_field(name="⚡ Why Choose Xyoo?", value="✅ Fast & Reliable\n🔒 Secure Payments\n🛡️ 24/7 Support\n⭐ Premium Quality", inline=True)
    embed.add_field(name="🎁 Special Perks", value="🔥 Great Prices\n📝 Customer Reviews\n🚀 Quick Delivery\n💝 Loyalty Rewards", inline=True)
    embed.set_image(url=YOUR_IMAGE_URL)
    embed.set_footer(text="Xyoo Shop • Happy Shopping!")
    return embed

def get_tutorial_embed():
    embed = discord.Embed(
        title="📋 How To Order - Instructions",
        description="▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n📚 **Follow these simple steps!**\n▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬",
        color=EMBED_COLOR
    )
    embed.add_field(
        name="📌 Step‑by‑Step Guide",
        value="```\n1️⃣ Browse our website 🛍️\n2️⃣ Choose your game & product\n3️⃣ Add items to your cart\n4️⃣ Proceed to checkout\n5️⃣ Select your payment method (GCash or PayPal)\n6️⃣ Enter your Discord username\n7️⃣ Complete the payment & wait for delivery\n```",
        inline=False
    )
    embed.add_field(name="💡 Need Help?", value=f"📞 Contact <@{SUPPORT_USER_ID}> anytime!\nWe're here to assist you.", inline=False)
    embed.set_footer(text="Xyoo Shop • Happy shopping!")
    return embed

def get_payment_methods_embed():
    embed = discord.Embed(title="💳 Payment Methods", description="▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n🌟 **Choose your preferred payment method!**\n▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬", color=EMBED_COLOR)
    embed.add_field(name="💰 Available Methods", value="```💰 GCASH```\n```🌍 PAYPAL```", inline=False)
    embed.add_field(name="💡 Need Help?", value=f"📞 Contact <@{SUPPORT_USER_ID}>\n⏰ We're here 24/7!", inline=False)
    embed.set_footer(text="Xyoo Shop • Secure & Reliable Payments")
    return embed

def get_order_here_embed():
    embed = discord.Embed(title="🛍️ Order Here", description="▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n🎉 **Ready to shop at Xyoo?**\n▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬", color=EMBED_COLOR)
    embed.add_field(name="🌐 Visit Our Website", value=f"**[Click here to place your order]({WEBSITE_URL})**\n⚡ Fast Loading | 🔒 Secure Checkout", inline=False)
    embed.add_field(name="✨ What You'll Find", value="🛍️ Browse premium products\n🔐 Secure payment gateway\n💳 Multiple payment options", inline=False)
    embed.set_footer(text="Xyoo Shop • Thank you for shopping!")
    return embed

def get_prices_embed():
    products = bot.config.get("products", [])
    if not products:
        desc = "No products yet."
    else:
        lines = [f"• **{p['name']}**: ${p['price']:.2f}" for p in products]
        desc = "\n".join(lines)
    embed = discord.Embed(title="💰 Xyoo Shop – Price List", description=desc, color=EMBED_COLOR)
    embed.set_footer(text="Prices in USD • Use /addproduct or /setprice")
    return embed

def get_order_embed(order_data, customer_discord, customer_added, member):
    items_text = "\n".join([f"• `{item['quantity']}x` **{item['name']}** — ${item['price']:.2f}" for item in order_data.get('items', [])]) or "No items"
    embed = discord.Embed(title="📦 New Web Order", description=f"**Order ID:** `{order_data.get('orderId')}`", color=EMBED_COLOR, timestamp=datetime.datetime.now())
    embed.add_field(name="💰 Total", value=f"**${order_data.get('total'):.2f}**", inline=True)
    embed.add_field(name="💳 Payment", value=order_data.get('paymentMethod', 'Unknown'), inline=True)
    embed.add_field(name="📅 Date", value=order_data.get('date', 'Unknown'), inline=True)
    if customer_discord:
        status = "✅ **Added**" if customer_added else ("⚠️ **Failed to add**" if member else "❌ **Not found**")
        embed.add_field(name="👤 Discord User", value=f"{customer_discord}\n{status}", inline=False)
    embed.add_field(name="🛒 Items", value=items_text, inline=False)
    embed.set_footer(text="Xyoo Shop • Web Order")
    return embed

def get_vouch_request_embed():
    embed = discord.Embed(title="⭐ Transaction Complete!", description="▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n🎉 **Thank you for shopping at Xyoo Shop!**\n▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n\nWe'd love to hear about your experience!\nClick the button below to leave a vouch — it helps us a lot! 💝", color=GOLD_COLOR)
    embed.set_footer(text="Xyoo Shop • After leaving a vouch, this thread will close automatically.")
    return embed

def get_close_embed():
    embed = discord.Embed(title="🔒 Thread Closing", description="▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\nThis thread has been closed by the owner.\nThank you! Goodbye! 👋\n▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬", color=EMBED_COLOR, timestamp=datetime.datetime.now())
    embed.set_footer(text="Xyoo Shop • Thread closed")
    return embed

# ================== UI COMPONENTS ==================
class XyooSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Instructions How To Order", value="tutorial", emoji="📋"),
            discord.SelectOption(label="Payment Methods Available", value="payment_methods", emoji="💳"),
            discord.SelectOption(label="Order Here", value="order_here", emoji="🛍️"),
            discord.SelectOption(label="View Prices", value="prices", emoji="💰"),
        ]
        super().__init__(placeholder="Choose an option...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        selected = self.values[0]
        if selected == "tutorial":
            await interaction.followup.send(embed=get_tutorial_embed(), ephemeral=True)
        elif selected == "payment_methods":
            await interaction.followup.send(embed=get_payment_methods_embed(), ephemeral=True)
        elif selected == "order_here":
            personal_link = f"{WEBSITE_URL}?user={interaction.user.id}"
            embed = discord.Embed(
                title="🛍️ Order Here",
                description=f"**[Click here to place your order]({personal_link})**\n⚡ Fast Loading | 🔒 Secure Checkout",
                color=EMBED_COLOR
            )
            embed.set_footer(text="Xyoo Shop • Thank you for shopping!")
            await interaction.followup.send(embed=embed, ephemeral=True)
        elif selected == "prices":
            await interaction.followup.send(embed=get_prices_embed(), ephemeral=True)

class SelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(XyooSelect())

class PanelChannelSelect(discord.ui.ChannelSelect):
    def __init__(self):
        super().__init__(placeholder="Choose a channel...", min_values=1, max_values=1, channel_types=[discord.ChannelType.text])

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            channel = interaction.guild.get_channel(self.values[0].id)
            if not channel:
                await interaction.followup.send("❌ Channel not found.", ephemeral=True)
                return
            bot.config["order_channel_id"] = channel.id
            save_config(bot.config)
            embed = get_main_embed()
            await channel.send(embed=embed, view=SelectView())
            await interaction.followup.send(f"✅ Panel posted in {channel.mention}!\nOrder threads will appear here.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)

class PanelSetupView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(PanelChannelSelect())

class VouchModal(discord.ui.Modal, title="⭐ Leave a Vouch"):
    vouch_message = discord.ui.TextInput(label="Your vouch message", style=discord.TextStyle.paragraph, max_length=500, required=True)

    async def on_submit(self, interaction: discord.Interaction):
        vouch_channel_id = VOUCH_CHANNEL_ID or bot.config.get("vouch_channel_id")
        if not vouch_channel_id:
            await interaction.response.send_message("❌ Vouch channel not configured.", ephemeral=True)
            return
        vouch_channel = interaction.guild.get_channel(vouch_channel_id)
        if not vouch_channel:
            await interaction.response.send_message("❌ Vouch channel not found.", ephemeral=True)
            return
        embed = discord.Embed(title="⭐ New Vouch", description=self.vouch_message.value, color=GOLD_COLOR, timestamp=datetime.datetime.now())
        embed.set_author(name=f"{interaction.user.display_name} (@{interaction.user.name})", icon_url=interaction.user.display_avatar.url)
        embed.add_field(name="User ID", value=f"`{interaction.user.id}`", inline=True)
        embed.add_field(name="Thread", value=interaction.channel.mention, inline=True)
        embed.set_footer(text="Xyoo Shop • Verified Purchase")
        await vouch_channel.send(embed=embed)
        await interaction.response.send_message("✅ Thank you for your vouch! Thread will close in 5 seconds...")
        if isinstance(interaction.channel, discord.Thread):
            asyncio.create_task(close_thread_after_delay(interaction.channel, 5))

class VouchButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Leave a Vouch", style=discord.ButtonStyle.success, emoji="⭐")
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(VouchModal())

class VouchRequestView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(VouchButton())

async def close_thread_after_delay(thread, seconds):
    await asyncio.sleep(seconds)
    try:
        await thread.edit(archived=True, locked=True)
    except Exception:
        pass

# ================== SLASH COMMANDS ==================
@app_commands.command(name="ping", description="🏓 Ping the bot")
async def ping_command(interaction: discord.Interaction):
    await interaction.response.send_message(f"🏓 Pong! {bot.latency*1000:.0f}ms", ephemeral=True)

@app_commands.command(name="xyoo", description="[Admin] Post the assistant panel")
@app_commands.default_permissions(administrator=True)
async def xyoo_command(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    view = PanelSetupView()
    await interaction.followup.send("📌 Choose a channel:", view=view, ephemeral=True)

@app_commands.command(name="setup", description="[Admin] Reconfigure order channel")
@app_commands.default_permissions(administrator=True)
async def setup_command(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    view = PanelSetupView()
    await interaction.followup.send("📌 Select a channel:", view=view, ephemeral=True)

@app_commands.command(name="request-vouch", description="[Admin] Ask for vouch (auto-closes)")
@app_commands.default_permissions(administrator=True)
async def request_vouch_command(interaction: discord.Interaction):
    await interaction.response.defer()
    if not isinstance(interaction.channel, discord.Thread):
        await interaction.followup.send("❌ Use inside an order thread.", ephemeral=True)
        return
    await interaction.followup.send(embed=get_vouch_request_embed(), view=VouchRequestView())

@app_commands.command(name="close", description="[Admin] Close thread without vouch")
@app_commands.default_permissions(administrator=True)
async def close_command(interaction: discord.Interaction):
    await interaction.response.defer()
    if not isinstance(interaction.channel, discord.Thread):
        await interaction.followup.send("❌ Use inside a thread.", ephemeral=True)
        return
    await interaction.followup.send(embed=get_close_embed())
    asyncio.create_task(close_thread_after_delay(interaction.channel, 5))

@app_commands.command(name="setprice", description="[Admin] Change the price of an existing product")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(item="Product name", price="New price in USD")
async def setprice_command(interaction: discord.Interaction, item: str, price: float):
    if price < 0:
        await interaction.response.send_message("❌ Price cannot be negative.", ephemeral=True)
        return
    products = bot.config.setdefault("products", [])
    for p in products:
        if p["name"] == item:
            p["price"] = round(price, 2)
            save_config(bot.config)
            await interaction.response.send_message(f"✅ Price for **{item}** set to **${price:.2f}** USD.", ephemeral=True)
            return
    await interaction.response.send_message(f"❌ Item **{item}** not found. Use /addproduct first.", ephemeral=True)

# ---------- ADD PRODUCT WITH IMAGE ATTACHMENT ----------
@app_commands.command(name="addproduct", description="[Admin] Add a new product (attach the image file)")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(
    name="Product name",
    price="Price in USD",
    category="Category (e.g. Pet, Seed)",
    image="Attach the product image (PNG/JPG)"
)
async def addproduct_command(
    interaction: discord.Interaction,
    name: str,
    price: float,
    category: str,
    image: discord.Attachment
):
    if price < 0:
        await interaction.response.send_message("❌ Price cannot be negative.", ephemeral=True)
        return

    products = bot.config.setdefault("products", [])
    if any(p["name"] == name for p in products):
        await interaction.response.send_message(f"❌ Product **{name}** already exists. Use /setprice to update it.", ephemeral=True)
        return

    # Save the attachment to static/ folder
    ext = os.path.splitext(image.filename)[1]  # e.g., ".png"
    clean_name = name.lower().replace(" ", "_").replace("'", "")
    filename = f"{clean_name}{ext}"
    filepath = os.path.join("static", filename)
    await image.save(filepath)

    new_id = bot.config.get("next_id", 1)
    new_product = {
        "id": new_id,
        "name": name,
        "price": round(price, 2),
        "image": filename,          # just the filename, website will use /static/<filename>
        "category": category
    }
    products.append(new_product)
    bot.config["next_id"] = new_id + 1
    save_config(bot.config)

    await interaction.response.send_message(
        f"✅ Added **{name}** (${price:.2f}) with ID {new_id}.\nImage saved as `{filename}`",
        ephemeral=True
    )

@app_commands.command(name="removeitem", description="[Admin] Remove a product from the shop")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(item="Product name to remove")
async def removeitem_command(interaction: discord.Interaction, item: str):
    products = bot.config.setdefault("products", [])
    for i, p in enumerate(products):
        if p["name"] == item:
            del products[i]
            save_config(bot.config)
            await interaction.response.send_message(f"🗑️ Removed **{item}** from the shop.", ephemeral=True)
            return
    await interaction.response.send_message(f"❌ Product **{item}** not found.", ephemeral=True)

@bot.command(name="sync")
@commands.is_owner()
async def sync_commands(ctx):
    await bot.tree.sync()
    await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
    await ctx.send("✅ Commands synced!")

def find_member(guild, query):
    if not query: return None
    query = query.strip()
    if query.isdigit():
        m = guild.get_member(int(query))
        if m: return m
    query_lower = query.lower()
    for m in guild.members:
        if (m.name.lower() == query_lower or m.display_name.lower() == query_lower or (m.global_name and m.global_name.lower() == query_lower)):
            return m
    for m in guild.members:
        if query_lower in m.name.lower() or query_lower in m.display_name.lower() or (m.global_name and query_lower in m.global_name.lower()):
            return m
    return None

async def process_order(order_data):
    await bot.wait_until_ready()
    guild = bot.get_guild(GUILD_ID)
    if not guild: return None
    channel = None
    if ORDER_CHANNEL_ID: channel = guild.get_channel(ORDER_CHANNEL_ID)
    if not channel: channel = guild.get_channel(bot.config.get("order_channel_id"))
    if not channel: channel = discord.utils.get(guild.text_channels, name="orders")
    if not channel: channel = guild.text_channels[0]
    if not channel: return None

    thread = await channel.create_thread(
        name=f"🛍️ ORDER - {order_data.get('orderId', 'Unknown')}",
        type=discord.ChannelType.private_thread,
        auto_archive_duration=1440
    )
    support = guild.get_member(SUPPORT_USER_ID)
    if support: await thread.add_user(support)

    customer_discord = order_data.get('discordUser', '').strip()
    customer_added = False
    member = None
    if customer_discord:
        member = find_member(guild, customer_discord)
        if member:
            await channel.set_permissions(member,
                send_messages_in_threads=True,
                read_messages=True,
                attach_files=True
            )
            await thread.add_user(member)
            customer_added = True

    embed = get_order_embed(order_data, customer_discord, customer_added, member)
    await thread.send(embed=embed)

    ping = f"📢 New order! <@{SUPPORT_USER_ID}>"
    if customer_discord:
        if customer_added:
            ping += f"\n{member.mention} Please send your payment receipt here to claim your order."
        else:
            ping += f"\n⚠️ Customer `{customer_discord}` was not found. They may need to be added manually."
    await thread.send(ping)
    return thread.id

# ================== QUART ROUTES ==================
@app.route('/')
async def index(): return await send_file('index.html')

@app.route('/payment-gcash.html')
async def gcash(): return await send_file('payment-gcash.html')

@app.route('/payment-paypal.html')
async def paypal(): return await send_file('payment-paypal.html')

@app.route('/health')
async def health(): return jsonify({"status": "ok"}), 200

@app.route('/api/products')
async def get_products():
    products = bot.config.get("products", [])
    return jsonify(products)

@app.route('/api/prices')
async def get_prices_legacy():
    products = bot.config.get("products", [])
    prices = {p["name"]: p["price"] for p in products}
    return jsonify(prices)

@app.route('/api/user/<int:user_id>')
async def get_user(user_id):
    guild = bot.get_guild(GUILD_ID)
    if not guild:
        return jsonify({"error": "Guild not found"}), 404
    member = guild.get_member(user_id)
    if not member:
        return jsonify({"error": "User not found"}), 404
    return jsonify({
        "id": member.id,
        "username": member.name,
        "display_name": member.display_name,
        "avatar_url": str(member.display_avatar.url)
    })

@app.route('/api/user/orders/<int:user_id>', methods=['GET'])
async def get_user_orders(user_id):
    guild = bot.get_guild(GUILD_ID)
    if not guild or not guild.get_member(user_id):
        return jsonify({"error": "User not found"}), 404
    orders = bot.config.get("user_orders", {}).get(str(user_id), [])
    return jsonify(orders)

@app.route('/api/user/orders', methods=['POST'])
async def save_user_order():
    if request.headers.get('X-API-Key') != API_KEY:
        return jsonify({"error": "Unauthorized"}), 401
    data = await request.get_json()
    user_id = data.get('user_id')
    if not user_id:
        return jsonify({"error": "user_id required"}), 400
    guild = bot.get_guild(GUILD_ID)
    if not guild or not guild.get_member(int(user_id)):
        return jsonify({"error": "User not in server"}), 404
    if "user_orders" not in bot.config:
        bot.config["user_orders"] = {}
    user_orders = bot.config["user_orders"].setdefault(str(user_id), [])
    order_copy = {k: v for k, v in data.items() if k != 'user_id'}
    user_orders.append(order_copy)
    save_config(bot.config)
    return jsonify({"status": "ok"}), 201

@app.route('/api/order', methods=['POST'])
async def receive_order():
    if request.headers.get('X-API-Key') != API_KEY:
        return jsonify({"error": "Unauthorized"}), 401
    data = await request.get_json()
    thread_id = await process_order(data)
    return jsonify({"status": "ok", "thread_id": str(thread_id) if thread_id else None}), 200

@bot.event
async def on_ready():
    logger.info(f"✅ Bot online as {bot.user}")

async def main():
    await asyncio.gather(
        bot.start(DISCORD_TOKEN),
        app.run_task(host='0.0.0.0', port=PORT)
    )

if __name__ == "__main__":
    if not DISCORD_TOKEN or not API_KEY:
        raise ValueError("Missing DISCORD_TOKEN or API_SECRET environment variables!")
    asyncio.run(main())