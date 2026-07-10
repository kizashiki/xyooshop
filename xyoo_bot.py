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
ORDER_CATEGORY_ID = 1404156170201075873          # Your order category ID
SUPPORT_USER_ID = 592402229978333331             # Your Discord user ID
VOUCH_CHANNEL_ID = 1393165027707588749           # Your vouch channel ID

EMBED_COLOR = discord.Color.from_rgb(186, 85, 211)
GOLD_COLOR = discord.Color.gold()
GREEN_COLOR = discord.Color.green()
RED_COLOR = discord.Color.red()

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

CONFIG_FILE = "bot_config.json"

# ----- GCASH IMAGE SETTINGS -----
GCASH_IMAGE_FILENAME = "gcash-qr.jpg"            # Must be in bot folder
GCASH_NUMBER = "0948 875 4669"                   # Replace with real number

# PayPal message (exact emoji tags you provided)
PAYPAL_MESSAGE = (
    "<a:onlen:1347265878646853656> **Make sure to select __Friends and Family__ and not the other option, so the money won't be put on hold.**\n\n"
    "<a:PayPal~1:1327594224035823677> **ALWAYS SEND RECEIPT** <a:PayPal~1:1327594224035823677>\n\n"
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

# ================== IMPROVED ITEM PARSER ==================
def parse_items(content: str):
    """
    Parse the price list into dropdown items.
    Skips headers like __HEADER__, lines without /$, and markdown-only lines.
    Handles bold markers (**Item** - 1/$2) and regular items.
    Returns list of dicts: {"label": "Hypno Bloom Seed – $2", "line": original line}
    """
    items = []
    for raw_line in content.split('\n'):
        line = raw_line.strip()
        # Skip empty lines, headers, and lines without price
        if not line or line.startswith('#') or line.startswith('__') or '@everyone' in line:
            continue
        if '/$' not in line:
            continue

        # Remove leading dash and spaces
        clean_line = line.lstrip('- ').strip()
        # Remove bold markers if present
        clean_line = clean_line.strip('*').strip()

        # Try to separate name and price part using ' - '
        if ' - ' in clean_line and '/$' in clean_line:
            name_part, price_part = clean_line.rsplit(' - ', 1)
            price_val = price_part.split('/$')[-1].strip()
            # Build a clean label
            label = f"{name_part.strip()} – ${price_val}"
            items.append({"label": label, "line": line})
        else:
            # Fallback: just use the line as label and value
            items.append({"label": clean_line, "line": line})
    return items

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
    embed.add_field(name="📋 Available Options", value="📋 **Instructions How To Order**\n💳 **Payment Methods**\n🛍️ **Order Here**", inline=False)
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
        value="```\n1️⃣ Click 'Order Here'\n2️⃣ Pick a game\n3️⃣ Choose item & quantity (no typing)\n4️⃣ Select payment method\n5️⃣ Your ticket is created\n```",
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

# ================== ORDER FLOW (Single ephemeral dialog) ==================
async def start_order_flow(interaction: discord.Interaction):
    if not bot.forum_cache:
        await interaction.followup.send("❌ No products available right now.", ephemeral=True)
        return

    # Send a placeholder and capture the message for editing
    await interaction.followup.send("Loading...", ephemeral=True)
    original_msg = await interaction.original_response()

    # Step 1: Game selection
    options = [discord.SelectOption(label=name, value=name) for name in bot.forum_cache.keys()]
    game_select = discord.ui.Select(placeholder="Choose a game...", options=options)

    view = discord.ui.View(timeout=300)
    view.add_item(game_select)
    await original_msg.edit(content="🎮 **Select a game:**", view=view)

    async def on_game_select(sel_inter: discord.Interaction):
        game = sel_inter.data["values"][0]
        content = bot.forum_cache[game]
        items = parse_items(content)

        if not items:
            # Fallback: show manual modal button
            await sel_inter.response.edit_message(
                content=f"**{game}**\n\n{content}",
                view=None
            )
            modal_btn = discord.ui.Button(label="Enter Order Details", style=discord.ButtonStyle.success)
            modal_view = discord.ui.View(timeout=300)

            async def open_modal(btn_inter: discord.Interaction):
                await btn_inter.response.send_modal(OrderDetailModal(game))

            modal_btn.callback = open_modal
            modal_view.add_item(modal_btn)
            await original_msg.edit(view=modal_view)
            return

        # Build item selection
        item_opts = [
            discord.SelectOption(label=it["label"][:100], value=it["line"]) for it in items
        ]
        item_select = discord.ui.Select(placeholder="Select an item...", options=item_opts)

        async def on_item_select(item_inter: discord.Interaction):
            item_line = item_inter.data["values"][0]
            # Quantity selection
            qty_opts = [discord.SelectOption(label=str(i), value=str(i)) for i in range(1, 11)]
            qty_select = discord.ui.Select(placeholder="Select quantity", options=qty_opts)

            async def on_qty_select(qty_inter: discord.Interaction):
                qty = int(qty_inter.data["values"][0])
                # Extract price
                if "/$" not in item_line:
                    await qty_inter.response.edit_message(content="❌ Invalid item format.", view=None)
                    return
                # Clean the line to extract price
                clean = item_line.strip('- ').strip('*').strip()
                price_str = clean.rsplit("/$", 1)[1].strip()
                try:
                    price = float(price_str)
                except ValueError:
                    await qty_inter.response.edit_message(content="❌ Invalid price.", view=None)
                    return

                total = price * qty
                order_data = {
                    "game": game,
                    "item_line": item_line,
                    "qty": qty,
                    "total": total,
                    "user_id": qty_inter.user.id,
                    "user_name": str(qty_inter.user),
                }

                # Payment selection
                pay_view = discord.ui.View(timeout=120)

                async def gcash_cb(pay_int: discord.Interaction):
                    await pay_int.response.defer()
                    order_data["payment"] = "GCash"
                    await create_order_ticket(pay_int, order_data)
                    await original_msg.edit(content="✅ Order ticket created! Check your private channel.", view=None)

                async def paypal_cb(pay_int: discord.Interaction):
                    await pay_int.response.defer()
                    order_data["payment"] = "PayPal"
                    await create_order_ticket(pay_int, order_data)
                    await original_msg.edit(content="✅ Order ticket created! Check your private channel.", view=None)

                gcash_btn = discord.ui.Button(label="💰 GCash", style=discord.ButtonStyle.primary)
                paypal_btn = discord.ui.Button(label="🌍 PayPal", style=discord.ButtonStyle.primary)
                gcash_btn.callback = gcash_cb
                paypal_btn.callback = paypal_cb
                pay_view.add_item(gcash_btn)
                pay_view.add_item(paypal_btn)

                await qty_inter.response.edit_message(
                    content=f"**Order Summary**\n• Game: {game}\n• Item: {item_line}\n• Quantity: {qty}\n• Total: **${total:.2f}**\n\n💳 **Select payment method:**",
                    view=pay_view
                )

            qty_select.callback = on_qty_select
            qty_view = discord.ui.View(timeout=120)
            qty_view.add_item(qty_select)
            await item_inter.response.edit_message(
                content=f"**Item:** {item_line}\n📦 **Select quantity:**",
                view=qty_view
            )

        item_select.callback = on_item_select
        item_view = discord.ui.View(timeout=300)
        item_view.add_item(item_select)
        await sel_inter.response.edit_message(
            content=f"**{game}** – Choose an item:",
            view=item_view
        )

    game_select.callback = on_game_select

# ================== FALLBACK ORDER MODAL ==================
class OrderDetailModal(discord.ui.Modal, title="Enter Your Order"):
    item_line = discord.ui.TextInput(
        label="Item Line",
        placeholder="e.g. Hypno Bloom Seed - 1/$2",
        required=True,
        max_length=100
    )
    quantity = discord.ui.TextInput(
        label="Quantity",
        placeholder="e.g. 2",
        required=True,
        max_length=5
    )

    def __init__(self, game_name: str):
        super().__init__()
        self.game_name = game_name

    async def on_submit(self, interaction: discord.Interaction):
        item_line = self.item_line.value.strip()
        qty_str = self.quantity.value.strip()
        if not qty_str.isdigit():
            await interaction.response.send_message("❌ Quantity must be a number.", ephemeral=True)
            return
        qty = int(qty_str)
        if qty <= 0:
            await interaction.response.send_message("❌ Quantity must be at least 1.", ephemeral=True)
            return
        if "/$" not in item_line:
            await interaction.response.send_message("❌ Could not find price. Use format like `Name - 1/$2`.", ephemeral=True)
            return
        clean = item_line.strip('- ').strip('*').strip()
        price_str = clean.rsplit("/$", 1)[1].strip()
        try:
            price = float(price_str)
        except ValueError:
            await interaction.response.send_message("❌ Invalid price format.", ephemeral=True)
            return

        total = price * qty
        order_data = {
            "game": self.game_name,
            "item_line": item_line,
            "qty": qty,
            "total": total,
            "user_id": interaction.user.id,
            "user_name": str(interaction.user),
        }

        view = discord.ui.View(timeout=120)

        async def gcash_cb(pay_int: discord.Interaction):
            await pay_int.response.defer()
            order_data["payment"] = "GCash"
            await create_order_ticket(pay_int, order_data)

        async def paypal_cb(pay_int: discord.Interaction):
            await pay_int.response.defer()
            order_data["payment"] = "PayPal"
            await create_order_ticket(pay_int, order_data)

        gcash_btn = discord.ui.Button(label="💰 GCash", style=discord.ButtonStyle.primary)
        paypal_btn = discord.ui.Button(label="🌍 PayPal", style=discord.ButtonStyle.primary)
        gcash_btn.callback = gcash_cb
        paypal_btn.callback = paypal_cb
        view.add_item(gcash_btn)
        view.add_item(paypal_btn)

        await interaction.response.send_message(
            f"**Order Summary**\n• Game: {self.game_name}\n• Item: {item_line}\n• Quantity: {qty}\n• Total: **${total:.2f}**\n\nSelect payment method:",
            view=view,
            ephemeral=True
        )

# ================== VOUCHING SYSTEM ==================
class VouchModal(discord.ui.Modal, title="Leave a Vouch"):
    rating = discord.ui.TextInput(
        label="Rating (1-5)",
        placeholder="Enter a number from 1 to 5",
        required=True,
        min_length=1,
        max_length=1
    )
    review = discord.ui.TextInput(
        label="Your Review",
        style=discord.TextStyle.paragraph,
        placeholder="Tell us about your experience...",
        required=True,
        max_length=500
    )

    def __init__(self, customer: discord.Member, order_channel: discord.TextChannel):
        super().__init__()
        self.customer = customer
        self.order_channel = order_channel

    async def on_submit(self, interaction: discord.Interaction):
        try:
            rating = int(self.rating.value)
            if not 1 <= rating <= 5:
                raise ValueError
        except ValueError:
            await interaction.response.send_message("❌ Invalid rating. Please enter a number between 1 and 5.", ephemeral=True)
            return

        review_text = self.review.value
        vouch_channel = interaction.guild.get_channel(VOUCH_CHANNEL_ID)
        if not vouch_channel:
            await interaction.response.send_message("❌ Vouch channel not found.", ephemeral=True)
            return

        stars = "⭐" * rating
        embed = discord.Embed(
            title="🌟 New Vouch!",
            description=f"**Customer:** {self.customer.mention}\n**Rating:** {stars}\n**Review:** {review_text}",
            color=GOLD_COLOR,
            timestamp=datetime.datetime.now()
        )
        embed.set_footer(text=f"Order channel: {self.order_channel.name}")
        await vouch_channel.send(embed=embed)

        await interaction.response.send_message("✅ Thank you for your vouch! This channel will be closed shortly.", ephemeral=True)
        await self.order_channel.send(f"🌟 {self.customer.mention} left a vouch: {stars}")
        await asyncio.sleep(5)
        await self.order_channel.delete()

class VouchRequestView(discord.ui.View):
    def __init__(self, customer: discord.Member, order_channel: discord.TextChannel):
        super().__init__(timeout=600)
        self.customer = customer
        self.order_channel = order_channel

    @discord.ui.button(label="Leave a Vouch", style=discord.ButtonStyle.success, emoji="🌟")
    async def vouch_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.customer:
            await interaction.response.send_message("❌ Only the customer can leave a vouch.", ephemeral=True)
            return
        modal = VouchModal(self.customer, self.order_channel)
        await interaction.response.send_modal(modal)

    async def on_timeout(self):
        try:
            await self.order_channel.send("⏰ Vouch request timed out. Closing channel.")
        except Exception:
            pass
        await asyncio.sleep(2)
        try:
            await self.order_channel.delete()
        except Exception:
            pass

# ================== ORDER TICKET CREATION ==================
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

    embed = discord.Embed(
        title="📦 New Order",
        description=f"**Customer:** {interaction.user.mention}\n**Game:** {order['game']}\n**Item:** {order['item_line']}\n**Quantity:** {order['qty']}\n**Total:** ${order['total']:.2f}\n**Payment:** {order['payment']}",
        color=EMBED_COLOR
    )
    await channel.send(embed=embed)

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

    await channel.send(f"<@{SUPPORT_USER_ID}> New order received!")

# ================== SLASH COMMANDS ==================
@app_commands.command(name="refreshproducts", description="[Admin] Refresh the products cache immediately from the forum")
@app_commands.default_permissions(administrator=True)
async def refresh_products_command(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    await bot._refresh_products()
    await interaction.followup.send(f"✅ Products refreshed! {len(bot.forum_cache)} games loaded.", ephemeral=True)

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

@app_commands.command(name="request-vouch", description="[Admin] Ask the customer for a vouch and close the ticket")
@app_commands.default_permissions(administrator=True)
async def request_vouch_command(interaction: discord.Interaction):
    if interaction.channel.category_id != ORDER_CATEGORY_ID:
        await interaction.response.send_message("❌ This command can only be used in an order ticket channel.", ephemeral=True)
        return

    customer = None
    for member, overwrite in interaction.channel.overwrites.items():
        if isinstance(member, discord.Member) and not member.bot:
            if overwrite.read_messages is True:
                customer = member
                break

    if not customer:
        await interaction.response.send_message("❌ Could not determine the customer.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    embed = discord.Embed(
        title="🌟 Vouch Request",
        description=f"{customer.mention}, please take a moment to leave a vouch about your experience!",
        color=EMBED_COLOR
    )
    view = VouchRequestView(customer, interaction.channel)
    await interaction.channel.send(embed=embed, view=view)
    await interaction.followup.send("✅ Vouch request sent to the customer.", ephemeral=True)

@app_commands.command(name="close", description="[Admin] Force‑close the current order ticket channel")
@app_commands.default_permissions(administrator=True)
async def close_command(interaction: discord.Interaction):
    if interaction.channel.category_id != ORDER_CATEGORY_ID:
        await interaction.response.send_message("❌ This command can only be used in an order ticket channel.", ephemeral=True)
        return

    await interaction.response.send_message("🔒 Closing ticket...", ephemeral=True)
    await asyncio.sleep(2)
    await interaction.channel.delete()

@bot.command(name="sync")
@commands.is_owner()
async def sync_commands(ctx):
    await bot.tree.sync()
    await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
    await ctx.send("✅ Commands synced!")

# ================== STARTUP ==================
async def main():
    t = threading.Thread(target=run_web)
    t.daemon = True
    t.start()
    await bot.start(DISCORD_TOKEN)

if __name__ == "__main__":
    if not DISCORD_TOKEN:
        raise ValueError("Missing DISCORD_TOKEN environment variable!")
    asyncio.run(main())