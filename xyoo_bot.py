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
FORUM_CHANNEL_ID = 1523641316020326470
ORDER_CATEGORY_ID = 1404156170201075873
SUPPORT_USER_ID = 592402229978333331
VOUCH_CHANNEL_ID = 1393165027707588749

CYBER_PURPLE = discord.Color.from_rgb(186, 85, 211)
GOLD_COLOR = discord.Color.gold()
GREEN_COLOR = discord.Color.green()
RED_COLOR = discord.Color.red()

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

CONFIG_FILE = "bot_config.json"
ORDER_COUNTER_FILE = "order_counter.json"

# ----- GCASH IMAGE SETTINGS -----
GCASH_IMAGE_FILENAME = "gcash-qr.jpg"
GCASH_NUMBER = "0948 875 4669"   # replace with yours

# PayPal message (plain text – used inside an embed)
PAYPAL_MESSAGE = (
    "Make sure to select **__Friends and Family__ and not the other option**, so the money won't be put on hold.\n\n"
    "ALWAYS SEND RECEIPT\n\n"
    "https://www.paypal.com/paypalme/OfficialXyoo"
)

# ---------- ORDER COUNTER ----------
def load_order_counter():
    try:
        if os.path.exists(ORDER_COUNTER_FILE):
            with open(ORDER_COUNTER_FILE, "r") as f:
                return json.load(f).get("counter", 0)
    except:
        pass
    return 0

def save_order_counter(counter):
    with open(ORDER_COUNTER_FILE, "w") as f:
        json.dump({"counter": counter}, f)

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
    except:
        pass
    return {}

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

class XyooBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)
        self.config = load_config()
        self.forum_cache = {}
        self.order_counter = load_order_counter()

    async def setup_hook(self):
        self.tree.add_command(ping_command)
        self.tree.add_command(xyoo_command)
        self.tree.add_command(setup_command)
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
            except:
                continue
        self.forum_cache = cache
        logger.info(f"Refreshed forum cache: {len(cache)} threads")

bot = XyooBot()

# ================== PARSER ==================
def parse_items(content: str):
    items = []
    for raw_line in content.split('\n'):
        line = raw_line.strip()
        if not line or line.startswith('#') or line.startswith('__') or '@everyone' in line:
            continue
        if '/$' not in line:
            continue
        clean_line = line.lstrip('- ').strip().strip('*').strip()
        if ' - ' in clean_line and '/$' in clean_line:
            name_part, price_part = clean_line.rsplit(' - ', 1)
            price_val = price_part.split('/$')[-1].strip()
            label = f"{name_part.strip()} – ${price_val}"
            items.append({"label": label, "line": line})
        else:
            items.append({"label": clean_line, "line": line})
    return items

# ================== EMBED TEMPLATES ==================
def get_main_embed():
    embed = discord.Embed(
        title="🤖 Xyoo Auto‑Shop",
        description=(
            "```css\n"
            "▸ NEXT-GEN ORDER SYSTEM\n"
            "```\n"
            "Welcome to the future of shopping.\n"
            "Select an option below to begin."
        ),
        color=CYBER_PURPLE,
        timestamp=datetime.datetime.now()
    )
    embed.set_image(url=bot.config.get("image_url", ""))
    embed.set_footer(text="Xyoo Shop • Automated")
    return embed

# ================== UI COMPONENTS ==================
class XyooSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="📋 How To Order", value="tutorial"),
            discord.SelectOption(label="💳 Payment Methods", value="payment_methods"),
            discord.SelectOption(label="🛍️ Order Here", value="order_here"),
        ]
        super().__init__(placeholder="Navigate the system...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        selected = self.values[0]
        if selected == "tutorial":
            embed = discord.Embed(title="📋 How To Order", color=CYBER_PURPLE,
                description="1️⃣ Choose your game\n2️⃣ Pick item & quantity\n3️⃣ Pay using GCash/PayPal\n4️⃣ Your order is processed automatically")
            await interaction.followup.send(embed=embed, ephemeral=True)
        elif selected == "payment_methods":
            embed = discord.Embed(title="💳 Payment Methods", color=CYBER_PURPLE,
                description="**💰 GCash**\n**🌍 PayPal**\n\nAlways send receipt after payment.")
            await interaction.followup.send(embed=embed, ephemeral=True)
        elif selected == "order_here":
            await start_order_flow(interaction)

class SelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)   # Permanent panel
        self.add_item(XyooSelect())

class PanelChannelSelect(discord.ui.ChannelSelect):
    def __init__(self):
        super().__init__(placeholder="Choose a channel...", min_values=1, max_values=1, channel_types=[discord.ChannelType.text])

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        channel = interaction.guild.get_channel(self.values[0].id)
        if not channel:
            await interaction.followup.send("❌ Channel not found.", ephemeral=True)
            return
        bot.config["order_channel_id"] = channel.id
        save_config(bot.config)
        embed = get_main_embed()
        await channel.send(embed=embed, view=SelectView())
        await interaction.followup.send(f"✅ Panel posted in {channel.mention}!", ephemeral=True)

class PanelSetupView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(PanelChannelSelect())

# ================== ORDER FLOW (Guided dialog) ==================
async def start_order_flow(interaction: discord.Interaction):
    if not bot.forum_cache:
        await interaction.followup.send("❌ No products available.", ephemeral=True)
        return

    options = [discord.SelectOption(label=name, value=name) for name in bot.forum_cache.keys()]
    game_select = discord.ui.Select(placeholder="🎮 Select game...", options=options)
    view = discord.ui.View(timeout=300)
    view.add_item(game_select)

    # Step 1: game selection with guide
    embed = discord.Embed(title="🛍️ Auto‑Shop – Step 1", description="🎮 **Choose your game** ⬇️", color=CYBER_PURPLE)
    await interaction.followup.send(embed=embed, view=view, ephemeral=True)
    original_msg = await interaction.original_response()

    async def on_game_select(sel_inter: discord.Interaction):
        game = sel_inter.data["values"][0]
        content = bot.forum_cache[game]
        items = parse_items(content)
        if not items:
            await sel_inter.response.edit_message(content="No items found. Contact admin.", view=None, embed=None)
            return

        # Step 2: item selection
        item_opts = [discord.SelectOption(label=it["label"][:100], value=it["line"]) for it in items]
        item_select = discord.ui.Select(placeholder="📦 Select item...", options=item_opts)
        embed_item = discord.Embed(title=f"🎮 {game} – Step 2", description="📦 **Select the item you want to buy** ⬇️", color=CYBER_PURPLE)
        item_view = discord.ui.View(timeout=300)
        item_view.add_item(item_select)
        await sel_inter.response.edit_message(embed=embed_item, view=item_view)

        async def on_item_select(item_inter: discord.Interaction):
            item_line = item_inter.data["values"][0]

            # Step 3: quantity selection
            qty_opts = [discord.SelectOption(label=str(i), value=str(i)) for i in range(1, 11)]
            qty_select = discord.ui.Select(placeholder="🔢 Quantity", options=qty_opts)
            embed_qty = discord.Embed(title=f"📦 {item_line} – Step 3", description="🔢 **How many?** ⬇️", color=CYBER_PURPLE)
            qty_view = discord.ui.View(timeout=120)
            qty_view.add_item(qty_select)
            await item_inter.response.edit_message(embed=embed_qty, view=qty_view)

            async def on_qty_select(qty_inter: discord.Interaction):
                qty = int(qty_inter.data["values"][0])
                if "/$" not in item_line:
                    await qty_inter.response.edit_message(content="❌ Invalid item format.", view=None, embed=None)
                    return
                clean = item_line.strip('- ').strip('*').strip()
                price_str = clean.rsplit("/$", 1)[1].strip()
                try:
                    price = float(price_str)
                except:
                    await qty_inter.response.edit_message(content="❌ Invalid price.", view=None, embed=None)
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

                # Step 4: payment selection
                pay_view = discord.ui.View(timeout=120)

                async def gcash_cb(pay_int: discord.Interaction):
                    await pay_int.response.defer()
                    order_data["payment"] = "GCash"
                    await create_order_ticket(pay_int, order_data)
                    embed_done = discord.Embed(title="✅ Order Created", description="Check your private ticket channel.", color=GREEN_COLOR)
                    await original_msg.edit(embed=embed_done, view=None)

                async def paypal_cb(pay_int: discord.Interaction):
                    await pay_int.response.defer()
                    order_data["payment"] = "PayPal"
                    await create_order_ticket(pay_int, order_data)
                    embed_done = discord.Embed(title="✅ Order Created", description="Check your private ticket channel.", color=GREEN_COLOR)
                    await original_msg.edit(embed=embed_done, view=None)

                gcash_btn = discord.ui.Button(label="💰 GCash", style=discord.ButtonStyle.primary)
                paypal_btn = discord.ui.Button(label="🌍 PayPal", style=discord.ButtonStyle.primary)
                gcash_btn.callback = gcash_cb
                paypal_btn.callback = paypal_cb
                pay_view.add_item(gcash_btn)
                pay_view.add_item(paypal_btn)

                embed_summary = discord.Embed(title="📋 Order Summary", color=CYBER_PURPLE)
                embed_summary.add_field(name="Game", value=game, inline=True)
                embed_summary.add_field(name="Item", value=item_line, inline=False)
                embed_summary.add_field(name="Qty", value=qty, inline=True)
                embed_summary.add_field(name="Total", value=f"${total:.2f}", inline=True)
                embed_summary.set_footer(text="💳 Select payment method below")

                await qty_inter.response.edit_message(embed=embed_summary, view=pay_view)

            qty_select.callback = on_qty_select

        item_select.callback = on_item_select

    game_select.callback = on_game_select

# ================== TICKET DASHBOARD ==================
class TicketControlView(discord.ui.View):
    def __init__(self, order_id, customer, channel):
        super().__init__(timeout=None)
        self.order_id = order_id
        self.customer = customer
        self.channel = channel
        self.status = "pending"
        self.dashboard_msg = None
        self.payment_msg = None

    async def update_ticket_embed(self, interaction=None):
        status_map = {
            "pending": ("🟡 Pending Payment", "Please complete payment."),
            "paid": ("🟢 Payment Received", "Processing your order..."),
            "delivered": ("📦 Delivered", "Order delivered. Vouch if you can!"),
            "completed": ("✅ Completed", "Ticket closed."),
        }
        status_text, desc = status_map.get(self.status, ("Unknown", ""))
        embed = discord.Embed(title=f"🧾 Order {self.order_id}", color=CYBER_PURPLE, description=desc)
        embed.add_field(name="Status", value=status_text, inline=False)
        embed.add_field(name="Customer", value=self.customer.mention, inline=True)
        embed.set_footer(text="Xyoo Auto‑Shop")

        # Remove payment image if not pending
        if self.status != "pending":
            embed.set_image(url=None)

        # Auto‑delete the separate payment instructions (PayPal) when status leaves pending
        if self.payment_msg and self.status != "pending":
            try:
                await self.payment_msg.delete()
            except (discord.NotFound, discord.HTTPException):
                pass
            self.payment_msg = None

        self.update_buttons()

        if interaction:
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            # For initial send or non-interaction edit, update the stored dashboard message
            if self.dashboard_msg:
                await self.dashboard_msg.edit(embed=embed, view=self)

    def update_buttons(self):
        self.clear_items()
        if self.status == "pending":
            self.add_item(MarkPaidButton(self))
        elif self.status == "paid":
            self.add_item(MarkDeliveredButton(self))
        elif self.status == "delivered":
            self.add_item(RequestVouchButton(self))
        if self.status != "completed":
            self.add_item(CloseTicketButton(self, style=discord.ButtonStyle.danger))

class MarkPaidButton(discord.ui.Button):
    def __init__(self, parent_view):
        super().__init__(label="✅ Mark as Paid", style=discord.ButtonStyle.success)
        self.parent = parent_view

    async def callback(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator and interaction.user.id != SUPPORT_USER_ID:
            await interaction.response.send_message("❌ Only admins can use this.", ephemeral=True)
            return
        self.parent.status = "paid"
        await self.parent.update_ticket_embed(interaction)

class MarkDeliveredButton(discord.ui.Button):
    def __init__(self, parent_view):
        super().__init__(label="📦 Mark as Delivered", style=discord.ButtonStyle.primary)
        self.parent = parent_view

    async def callback(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator and interaction.user.id != SUPPORT_USER_ID:
            await interaction.response.send_message("❌ Only admins can use this.", ephemeral=True)
            return
        self.parent.status = "delivered"
        await self.parent.update_ticket_embed(interaction)

class RequestVouchButton(discord.ui.Button):
    def __init__(self, parent_view):
        super().__init__(label="🌟 Request Vouch", style=discord.ButtonStyle.secondary)
        self.parent = parent_view

    async def callback(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator and interaction.user.id != SUPPORT_USER_ID:
            await interaction.response.send_message("❌ Only admins can use this.", ephemeral=True)
            return
        vouch_view = VouchRequestView(self.parent.customer, self.parent.channel)
        embed = discord.Embed(title="🌟 Vouch Request", color=GOLD_COLOR,
                              description=f"{self.parent.customer.mention}, please leave a vouch about your experience!")
        await self.parent.channel.send(embed=embed, view=vouch_view)
        await interaction.response.send_message("✅ Vouch request sent.", ephemeral=True)

class CloseTicketButton(discord.ui.Button):
    def __init__(self, parent_view, style=discord.ButtonStyle.danger):
        super().__init__(label="🔒 Close Ticket", style=style)
        self.parent = parent_view

    async def callback(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator and interaction.user.id != SUPPORT_USER_ID:
            await interaction.response.send_message("❌ Only admins can use this.", ephemeral=True)
            return
        self.parent.status = "completed"
        embed = discord.Embed(title="🔒 Ticket Closed", color=RED_COLOR)
        await interaction.response.edit_message(embed=embed, view=None)
        await asyncio.sleep(3)
        await self.parent.channel.delete()

# ================== VOUCH SYSTEM ==================
class VouchModal(discord.ui.Modal, title="Leave a Vouch"):
    rating = discord.ui.TextInput(label="Rating (1-5)", placeholder="Enter a number from 1 to 5", required=True, min_length=1, max_length=1)
    review = discord.ui.TextInput(label="Your Review", style=discord.TextStyle.paragraph, placeholder="Tell us about your experience...", required=True, max_length=500)

    def __init__(self, customer: discord.Member, order_channel: discord.TextChannel):
        super().__init__()
        self.customer = customer
        self.order_channel = order_channel

    async def on_submit(self, interaction: discord.Interaction):
        try:
            rating = int(self.rating.value)
            if not 1 <= rating <= 5:
                raise ValueError
        except:
            await interaction.response.send_message("❌ Invalid rating.", ephemeral=True)
            return
        vouch_channel = interaction.guild.get_channel(VOUCH_CHANNEL_ID)
        if not vouch_channel:
            await interaction.response.send_message("❌ Vouch channel not found.", ephemeral=True)
            return
        stars = "⭐" * rating
        embed = discord.Embed(title="🌟 New Vouch!", color=GOLD_COLOR,
                              description=f"**Customer:** {self.customer.mention}\n**Rating:** {stars}\n**Review:** {self.review.value}")
        await vouch_channel.send(embed=embed)
        await interaction.response.send_message("✅ Thank you! Ticket will close shortly.", ephemeral=True)
        await self.order_channel.send(f"🌟 {self.customer.mention} left a vouch: {stars}")
        await asyncio.sleep(5)
        await self.order_channel.delete()

class VouchRequestView(discord.ui.View):
    def __init__(self, customer: discord.Member, order_channel: discord.TextChannel):
        super().__init__(timeout=600)
        self.customer = customer
        self.order_channel = order_channel

    @discord.ui.button(label="Leave a Vouch", style=discord.ButtonStyle.success, emoji="🌟")
    async def vouch_button(self, interaction: discord.Interaction, button):
        if interaction.user != self.customer:
            await interaction.response.send_message("❌ Only the customer can vouch.", ephemeral=True)
            return
        await interaction.response.send_modal(VouchModal(self.customer, self.order_channel))

    async def on_timeout(self):
        try:
            await self.order_channel.send("⏰ Vouch request timed out. Closing.")
        except:
            pass
        await asyncio.sleep(2)
        try:
            await self.order_channel.delete()
        except:
            pass

# ================== ORDER TICKET CREATION ==================
async def create_order_ticket(interaction: discord.Interaction, order):
    guild = interaction.guild
    category = guild.get_channel(ORDER_CATEGORY_ID)
    if not category:
        await interaction.followup.send("❌ Order category not configured.", ephemeral=True)
        return

    bot.order_counter += 1
    save_order_counter(bot.order_counter)
    order_id = f"#{bot.order_counter:04d}"

    channel = await guild.create_text_channel(
        name=f"order-{interaction.user.name}",
        category=category,
        overwrites={
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }
    )

    control_view = TicketControlView(order_id, interaction.user, channel)

    embed = discord.Embed(title=f"🧾 Order {order_id}", color=CYBER_PURPLE,
                          description="**Thank you for your order!**\nPlease complete payment below.")
    embed.add_field(name="Game", value=order['game'], inline=True)
    embed.add_field(name="Item", value=order['item_line'], inline=False)
    embed.add_field(name="Qty", value=order['qty'], inline=True)
    embed.add_field(name="Total", value=f"${order['total']:.2f}", inline=True)
    embed.add_field(name="Payment", value=order['payment'], inline=True)
    embed.add_field(name="Status", value="🟡 Pending Payment", inline=False)
    embed.set_footer(text="Xyoo Auto‑Shop • Automated")

    if order["payment"] == "GCash":
        if os.path.isfile(GCASH_IMAGE_FILENAME):
            file = discord.File(GCASH_IMAGE_FILENAME, filename="gcash-qr.jpg")
            embed.set_image(url="attachment://gcash-qr.jpg")
            dashboard_msg = await channel.send(embed=embed, file=file, view=control_view)
        else:
            dashboard_msg = await channel.send(embed=embed, view=control_view)
            await channel.send(f"📱 GCash Payment\nNumber: **{GCASH_NUMBER}**\n(QR image not found)")
        control_view.dashboard_msg = dashboard_msg
    else:
        dashboard_msg = await channel.send(embed=embed, view=control_view)
        paypal_embed = discord.Embed(
            title="🌍 PayPal Payment",
            description=PAYPAL_MESSAGE,
            color=CYBER_PURPLE
        )
        payment_msg = await channel.send(embed=paypal_embed)
        control_view.dashboard_msg = dashboard_msg
        control_view.payment_msg = payment_msg

    await channel.send(f"<@{SUPPORT_USER_ID}> New order!", delete_after=5)

# ================== SLASH COMMANDS ==================
@app_commands.command(name="refreshproducts", description="[Admin] Refresh product cache")
@app_commands.default_permissions(administrator=True)
async def refresh_products_command(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    await bot._refresh_products()
    await interaction.followup.send(f"✅ Products refreshed! {len(bot.forum_cache)} games.", ephemeral=True)

@app_commands.command(name="ping", description="🏓 Ping")
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

# Legacy commands redirect to dashboard
@app_commands.command(name="request-vouch", description="[Admin] Ask for vouch (legacy)")
@app_commands.default_permissions(administrator=True)
async def request_vouch_command(interaction: discord.Interaction):
    await interaction.response.send_message("Use the ticket dashboard buttons instead.", ephemeral=True)

@app_commands.command(name="close", description="[Admin] Close ticket (legacy)")
@app_commands.default_permissions(administrator=True)
async def close_command(interaction: discord.Interaction):
    await interaction.response.send_message("Use the ticket dashboard buttons instead.", ephemeral=True)

@bot.command(name="sync")
@commands.is_owner()
async def sync_commands(ctx):
    await bot.tree.sync()
    await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
    await ctx.send("✅ Synced!")

# ================== STARTUP ==================
async def main():
    t = threading.Thread(target=run_web)
    t.daemon = True
    t.start()
    await bot.start(DISCORD_TOKEN)

if __name__ == "__main__":
    if not DISCORD_TOKEN:
        raise ValueError("Missing DISCORD_TOKEN!")
    asyncio.run(main())