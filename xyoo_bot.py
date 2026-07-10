import os
import json
import discord
from discord.ext import commands, tasks
from discord import app_commands
import datetime
import logging
import asyncio
import threading
from flask import Flask

# ================== CONFIGURATION ==================
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
GUILD_ID = int(os.getenv('GUILD_ID', '1129463696737972267'))
FORUM_CHANNEL_ID = 1523641316020326470          # Your forum channel ID
ORDER_CATEGORY_ID = 1404156170201075873          # Your order category ID (hardcoded)
SUPPORT_USER_ID = 592402229978333331             # Your Discord user ID

EMBED_COLOR = discord.Color.from_rgb(186, 85, 211)
GOLD_COLOR = discord.Color.gold()
GREEN_COLOR = discord.Color.green()
RED_COLOR = discord.Color.red()

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

CONFIG_FILE = "bot_config.json"

# ----- GCASH IMAGE SETTINGS -----
GCASH_IMAGE_FILENAME = "gcash-qr.jpg"            # The image file must be in the bot's folder
GCASH_NUMBER = "0948 875 4669"                   # <-- REPLACE WITH YOUR REAL NUMBER

# PayPal message (plain text, so custom emojis render correctly)
PAYPAL_MESSAGE = (
    "<a:onlen:1347265878646853656> **Make sure to select __Friends and Family__ and not the other option, so the money won't be put on hold.**\n\n"
    "<a:PayPal:1327594224035823677> **ALWAYS SEND RECEIPT** <a:PayPal:1327594224035823677>\n\n"
    "https://www.paypal.com/paypalme/OfficialXyoo"
)

# ---------- DUMMY FLASK SERVER FOR RENDER ----------
app_web = Flask(__name__)

@app_web.route('/health')
def health():
    return "OK", 200

def run_web():
    port = int(os.environ.get('PORT', 8080))
    app_web.run(host='0.0.0.0', port=port)

def load_config():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return {}

def save_config(config):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=4)
    except Exception:
        pass

class XyooBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)
        self.config = load_config()
        self.forum_cache = {}

    async def setup_hook(self):
        self.tree.add_command(ping_command)
        self.tree.add_command(xyoo_command)
        self.tree.add_command(setup_command)
        self.tree.add_command(request_vouch_command)
        self.tree.add_command(close_command)
        self.tree.add_command(refresh_products_command)

        self.refresh_products.start()

        if os.getenv('SYNC_COMMANDS', 'false').lower() == 'true':
            await self.tree.sync()
            guild = discord.Object(id=GUILD_ID)
            await self.tree.sync(guild=guild)
            logger.info("Commands synced")
        else:
            logger.info("Skipping command sync")

    @tasks.loop(minutes=5)
    async def refresh_products(self):
        await self._refresh_products()

    @refresh_products.before_loop
    async def before_refresh(self):
        await self.wait_until_ready()

    async def _refresh_products(self):
        guild = self.get_guild(GUILD_ID)
        if not guild:
            return
        forum = guild.get_channel(FORUM_CHANNEL_ID)
        if not forum or not isinstance(forum, discord.ForumChannel):
            logger.error("FORUM_CHANNEL_ID is not a forum channel")
            return

        cache = {}
        for thread in forum.threads:
            try:
                messages = []
                async for msg in thread.history(limit=2, oldest_first=True):
                    messages.append(msg)
                if len(messages) >= 2:
                    cache[thread.name] = messages[1].content
                else:
                    starter = thread.starter_message
                    if starter is None:
                        starter = await thread.fetch_message(thread.id)
                    cache[thread.name] = starter.content
            except Exception:
                continue

        self.forum_cache = cache
        logger.info(f"Refreshed forum cache: {len(cache)} threads")

bot = XyooBot()

# ================== EMBED TEMPLATES ==================
def get_main_embed():
    embed = discord.Embed(
        title="🤖 Xyoo Assistant",
        description=(
            "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
            "✨ **Welcome to Xyoo Shop!** ✨\n"
            "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n\n"
            "Get everything you need with just one click!\n"
            "👇 **Select an option below to get started:**"
        ),
        color=EMBED_COLOR,
        timestamp=datetime.datetime.now()
    )
    embed.add_field(name="📋 Available Options", value="📋 **Instructions How To Order**\n💳 **Payment Methods**\n🛍️ **Order Here**\n💰 **View Prices**", inline=False)
    embed.add_field(name="⚡ Why Choose Xyoo?", value="✅ Fast & Reliable\n🔒 Secure Payments\n🛡️ 24/7 Support\n⭐ Premium Quality", inline=True)
    embed.add_field(name="🎁 Special Perks", value="🔥 Great Prices\n📝 Customer Reviews\n🚀 Quick Delivery\n💝 Loyalty Rewards", inline=True)
    embed.set_image(url=bot.config.get("image_url", ""))
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
        value="```\n1️⃣ Click 'Order Here' below\n2️⃣ Choose your game\n3️⃣ Copy the item line you want from the price list\n4️⃣ Paste it and add the quantity\n5️⃣ Select payment method (GCash or PayPal)\n6️⃣ Your order ticket will be created\n```",
        inline=False
    )
    embed.add_field(name="💡 Need Help?", value=f"📞 Contact <@{SUPPORT_USER_ID}> anytime!", inline=False)
    embed.set_footer(text="Xyoo Shop • Happy shopping!")
    return embed

def get_payment_methods_embed():
    embed = discord.Embed(title="💳 Payment Methods", description="▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n🌟 **Choose your preferred payment method!**\n▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬", color=EMBED_COLOR)
    embed.add_field(name="💰 Available Methods", value="```💰 GCASH```\n```🌍 PAYPAL```", inline=False)
    embed.add_field(name="💡 Need Help?", value=f"📞 Contact <@{SUPPORT_USER_ID}>\n⏰ We're here 24/7!", inline=False)
    embed.set_footer(text="Xyoo Shop • Secure & Reliable Payments")
    return embed

def get_prices_embed():
    if not bot.forum_cache:
        desc = "No products found."
    else:
        desc = ""
        for name, content in bot.forum_cache.items():
            desc += f"**{name}**\n{content}\n\n"
    embed = discord.Embed(title="💰 Xyoo Shop – Price List", description=desc[:4096], color=EMBED_COLOR)
    embed.set_footer(text="Prices are automatically read from the forum channel.")
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
            await start_order_flow(interaction)
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
            await interaction.followup.send(f"✅ Panel posted in {channel.mention}!", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)

class PanelSetupView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(PanelChannelSelect())

# ================== ORDER FLOW ==================
async def start_order_flow(interaction: discord.Interaction):
    if not bot.forum_cache:
        await interaction.followup.send("❌ No products available right now. Please try again later.", ephemeral=True)
        return

    view = discord.ui.View(timeout=300)
    options = [discord.SelectOption(label=name, value=name) for name in bot.forum_cache.keys()]
    game_select = discord.ui.Select(placeholder="Choose a game...", options=options)

    async def game_select_callback(select_interaction: discord.Interaction):
        await select_interaction.response.defer()
        selected_game = select_interaction.data["values"][0]
        content = bot.forum_cache.get(selected_game, "No content.")

        await interaction.followup.send(f"**{selected_game}**\n\n{content}", ephemeral=True)
        await interaction.followup.send(
            "Copy the **exact line** of the item you want (e.g. `Moon Bloom Seed - 1/$2`) and add the quantity, like this:\n"
            "`Moon Bloom Seed - 1/$2 2`",
            ephemeral=True
        )

        def check(msg):
            return msg.author == select_interaction.user and msg.channel == select_interaction.channel

        try:
            msg = await bot.wait_for("message", check=check, timeout=120)
            parts = msg.content.rsplit(" ", 1)
            if len(parts) != 2 or not parts[1].isdigit():
                await select_interaction.followup.send("Invalid format. Please include the item line and quantity.", ephemeral=True)
                return

            item_line = parts[0].strip()
            qty = int(parts[1])

            price = None
            if "/$" in item_line:
                price_part = item_line.rsplit("/$", 1)[1]
                try:
                    price = float(price_part)
                except ValueError:
                    await select_interaction.followup.send("Could not extract price from line.", ephemeral=True)
                    return
            else:
                await select_interaction.followup.send("Could not find price. Use lines like `Name - 1/$2`.", ephemeral=True)
                return

            total = price * qty
            order_data = {
                "game": selected_game,
                "item_line": item_line,
                "qty": qty,
                "total": total,
                "user_id": select_interaction.user.id,
                "user_name": str(select_interaction.user),
            }

            view_payment = discord.ui.View(timeout=120)
            async def gcash_callback(pay_int: discord.Interaction):
                await pay_int.response.defer()
                order_data["payment"] = "GCash"
                await create_order_ticket(pay_int, order_data)
            async def paypal_callback(pay_int: discord.Interaction):
                await pay_int.response.defer()
                order_data["payment"] = "PayPal"
                await create_order_ticket(pay_int, order_data)

            gcash_btn = discord.ui.Button(label="💰 GCash", style=discord.ButtonStyle.primary)
            paypal_btn = discord.ui.Button(label="🌍 PayPal", style=discord.ButtonStyle.primary)
            gcash_btn.callback = gcash_callback
            paypal_btn.callback = paypal_callback
            view_payment.add_item(gcash_btn)
            view_payment.add_item(paypal_btn)

            await select_interaction.followup.send(
                f"Order summary:\n- Game: {selected_game}\n- Item: {item_line}\n- Quantity: {qty}\n- Total: **${total:.2f}**\n\nSelect your payment method:",
                view=view_payment,
                ephemeral=True
            )
        except asyncio.TimeoutError:
            await select_interaction.followup.send("Timed out.", ephemeral=True)

    game_select.callback = game_select_callback
    view.add_item(game_select)
    await interaction.followup.send("Select the game you want to order from:", view=view, ephemeral=True)

async def create_order_ticket(interaction: discord.Interaction, order):
    guild = interaction.guild
    category = guild.get_channel(ORDER_CATEGORY_ID)
    if not category:
        await interaction.followup.send("❌ Order category not configured. Contact the owner.", ephemeral=True)
        return

    channel = await guild.create_text_channel(
        name=f"order-{interaction.user.name}",
        category=category,
        overwrites={
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }
    )

    # Order details embed
    embed = discord.Embed(
        title="📦 New Order",
        description=f"**Customer:** {interaction.user.mention}\n**Game:** {order['game']}\n**Item:** {order['item_line']}\n**Quantity:** {order['qty']}\n**Total:** ${order['total']:.2f}\n**Payment:** {order['payment']}",
        color=EMBED_COLOR
    )
    await channel.send(embed=embed)

    # Send payment instructions
    if order["payment"] == "GCash":
        if os.path.isfile(GCASH_IMAGE_FILENAME):
            file = discord.File(GCASH_IMAGE_FILENAME, filename="gcash-qr.jpg")
            gcash_embed = discord.Embed(
                title="📱 GCash Payment",
                description=f"Please send your payment to:\n**{GCASH_NUMBER}**\n\n📸 **After paying, post a screenshot of the receipt in this channel.**",
                color=GOLD_COLOR
            )
            gcash_embed.set_image(url="attachment://gcash-qr.jpg")
            await channel.send(file=file, embed=gcash_embed)
        else:
            await channel.send(f"📱 GCash Payment\nNumber: **{GCASH_NUMBER}**\n(QR image not found – please ask for it.)")
    else:
        await channel.send(PAYPAL_MESSAGE)

    # Ping the owner
    await channel.send(f"<@{SUPPORT_USER_ID}> New order received!")

    await interaction.followup.send(
        f"✅ Order ticket created: {channel.mention}. Please follow the payment instructions and post your receipt there.",
        ephemeral=True
    )

# ================== REFRESH COMMAND ==================
@app_commands.command(name="refreshproducts", description="[Admin] Refresh the products cache immediately from the forum")
@app_commands.default_permissions(administrator=True)
async def refresh_products_command(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    await bot._refresh_products()
    await interaction.followup.send(f"✅ Products refreshed! {len(bot.forum_cache)} games loaded.", ephemeral=True)

# ================== OTHER SLASH COMMANDS ==================
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
    pass

@app_commands.command(name="close", description="[Admin] Close thread without vouch")
@app_commands.default_permissions(administrator=True)
async def close_command(interaction: discord.Interaction):
    pass

@bot.command(name="sync")
@commands.is_owner()
async def sync_commands(ctx):
    await bot.tree.sync()
    await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
    await ctx.send("✅ Commands synced!")

# ================== STARTUP ==================
async def main():
    # Start the dummy web server in a thread for Render
    t = threading.Thread(target=run_web)
    t.daemon = True
    t.start()
    await bot.start(DISCORD_TOKEN)

if __name__ == "__main__":
    if not DISCORD_TOKEN:
        raise ValueError("Missing DISCORD_TOKEN environment variable!")
    asyncio.run(main())