import os
import json
import discord
from discord.ext import commands
from discord import app_commands
import datetime
import logging
import asyncio
from quart import Quart, request, jsonify, send_file

# ================== CONFIGURATION ==================
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
GUILD_ID = int(os.getenv('GUILD_ID', '1129463696737972267'))
ORDER_CHANNEL_ID = int(os.getenv('ORDER_CHANNEL_ID', '0'))
API_KEY = os.getenv('API_SECRET', 'change-me-in-production')
PORT = int(os.getenv('PORT', 8080))
SUPPORT_USER_ID = 592402229978333331
WEBSITE_URL = "https://xyoo-shop.up.railway.app"
VOUCH_CHANNEL_ID = int(os.getenv('VOUCH_CHANNEL_ID', '0'))

# 🖼️ REPLACE THIS WITH YOUR DIRECT IMAGE URL
YOUR_IMAGE_URL = "https://cdn.discordapp.com/attachments/1124170237089165325/1496726350101217402/standard.gif?ex=69eaee89&is=69e99d09&hm=552bc026ea5a3921bcc609650566bac8f6bb09e256022d690f717abffa54fa0b"

EMBED_COLOR = discord.Color.from_rgb(186, 85, 211)  # Purple
GOLD_COLOR = discord.Color.gold()
GREEN_COLOR = discord.Color.green()
RED_COLOR = discord.Color.red()

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

app = Quart(__name__, static_folder='static', static_url_path='/static')
CONFIG_FILE = "bot_config.json"

def load_config():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
    return {}

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
        # ✅ Register commands BEFORE syncing
        self.tree.add_command(ping_command)
        self.tree.add_command(xyoo_command)
        self.tree.add_command(setup_command)
        self.tree.add_command(request_vouch_command)
        self.tree.add_command(close_command)

        if os.getenv('SYNC_COMMANDS', 'false').lower() == 'true':
            await self.tree.sync()
            guild = discord.Object(id=GUILD_ID)
            await self.tree.sync(guild=guild)
            logger.info("✅ Commands synced")
        else:
            logger.info("Skipping command sync (SYNC_COMMANDS not set)")

bot = XyooBot()

# ================== ENHANCED EMBED TEMPLATES ==================

def get_main_embed():
    """Main panel embed with attractive design and animated banner."""
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
    embed.add_field(
        name="📋 Available Options",
        value=(
            "🎥 **Video How To Order**\n"
            "💳 **Payment Methods**\n"
            "🛍️ **Order Here**"
        ),
        inline=False
    )
    embed.add_field(
        name="⚡ Why Choose Xyoo?",
        value=(
            "✅ Fast & Reliable\n"
            "🔒 Secure Payments\n"
            "🛡️ 24/7 Support\n"
            "⭐ Premium Quality"
        ),
        inline=True
    )
    embed.add_field(
        name="🎁 Special Perks",
        value=(
            "🔥 Great Prices\n"
            "📝 Customer Reviews\n"
            "🚀 Quick Delivery\n"
            "💝 Loyalty Rewards"
        ),
        inline=True
    )
    # ✅ Animated banner added here
    embed.set_image(url=YOUR_IMAGE_URL)
    embed.set_footer(text="Xyoo Shop • Happy Shopping!")
    return embed


def get_tutorial_embed():
    """Enhanced tutorial embed."""
    embed = discord.Embed(
        title="🎥 How To Order - Tutorial",
        description=(
            "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
            "📚 **Follow our easy step-by-step guide!**\n"
            "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬"
        ),
        color=EMBED_COLOR
    )
    embed.add_field(
        name="📹 Video Tutorial",
        value="[🎬 Click here to watch!](https://www.youtube.com/)\n⏱️ Duration: ~5 minutes",
        inline=False
    )
    embed.add_field(
        name="📋 Quick Steps",
        value=(
            "```\n"
            "1️⃣ Browse products 🛍️\n"
            "2️⃣ Select item ⭐\n"
            "3️⃣ Choose payment 💳\n"
            "4️⃣ Complete transaction ✨\n"
            "5️⃣ Receive product! 🎉\n"
            "```"
        ),
        inline=False
    )
    embed.set_footer(text="Xyoo Shop • Need help? Contact support!")
    return embed


def get_payment_methods_embed():
    """Enhanced payment methods embed."""
    embed = discord.Embed(
        title="💳 Payment Methods",
        description=(
            "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
            "🌟 **Choose your preferred payment method!**\n"
            "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬"
        ),
        color=EMBED_COLOR
    )
    embed.add_field(
        name="💰 Available Methods",
        value=(
            "```💰 GCASH```\n"
            "```🌍 PAYPAL```\n"
            "```🎮 ROBUX GIFT CARD```"
        ),
        inline=False
    )
    embed.add_field(
        name="💡 Need Help?",
        value=f"📞 Contact <@{SUPPORT_USER_ID}>\n⏰ We're here 24/7!",
        inline=False
    )
    embed.set_footer(text="Xyoo Shop • Secure & Reliable Payments")
    return embed


def get_order_here_embed():
    """Enhanced order here embed."""
    embed = discord.Embed(
        title="🛍️ Order Here",
        description=(
            "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
            "🎉 **Ready to shop at Xyoo?**\n"
            "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬"
        ),
        color=EMBED_COLOR
    )
    embed.add_field(
        name="🌐 Visit Our Website",
        value=f"**[Click here to place your order]({WEBSITE_URL})**\n⚡ Fast Loading | 🔒 Secure Checkout",
        inline=False
    )
    embed.add_field(
        name="✨ What You'll Find",
        value=(
            "🛍️ Browse premium products\n"
            "🔐 Secure payment gateway\n"
            "💳 Multiple payment options"
        ),
        inline=False
    )
    embed.set_footer(text="Xyoo Shop • Thank you for shopping!")
    return embed


def get_order_embed(order_data, customer_discord, customer_added, member):
    """Enhanced order confirmation embed for thread."""
    items_text = "\n".join([
        f"• `{item['quantity']}x` **{item['name']}** — ${item['price']:.2f}"
        for item in order_data.get('items', [])
    ]) or "No items"

    embed = discord.Embed(
        title="📦 New Web Order",
        description=f"**Order ID:** `{order_data.get('orderId')}`",
        color=EMBED_COLOR,
        timestamp=datetime.datetime.now()
    )
    embed.add_field(name="💰 Total", value=f"**${order_data.get('total'):.2f}**", inline=True)
    embed.add_field(name="💳 Payment", value=order_data.get('paymentMethod', 'Unknown'), inline=True)
    embed.add_field(name="📅 Date", value=order_data.get('date', 'Unknown'), inline=True)

    if customer_discord:
        if customer_added:
            status = "✅ **Added**"
        elif member:
            status = "⚠️ **Failed to add**"
        else:
            status = "❌ **Not found**"
        embed.add_field(name="👤 Discord User", value=f"{customer_discord}\n{status}", inline=False)

    embed.add_field(name="🛒 Items", value=items_text, inline=False)
    embed.set_footer(text="Xyoo Shop • Web Order")
    return embed


def get_vouch_request_embed():
    """Enhanced vouch request embed."""
    embed = discord.Embed(
        title="⭐ Transaction Complete!",
        description=(
            "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
            "🎉 **Thank you for shopping at Xyoo Shop!**\n"
            "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n\n"
            "We'd love to hear about your experience!\n"
            "Click the button below to leave a vouch — it helps us a lot! 💝"
        ),
        color=GOLD_COLOR
    )
    embed.set_footer(text="Xyoo Shop • After leaving a vouch, this thread will close automatically.")
    return embed


def get_close_embed():
    """Enhanced thread close embed."""
    embed = discord.Embed(
        title="🔒 Thread Closing",
        description=(
            "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
            "This thread has been closed by the owner.\n"
            "Thank you! Goodbye! 👋\n"
            "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬"
        ),
        color=EMBED_COLOR,
        timestamp=datetime.datetime.now()
    )
    embed.set_footer(text="Xyoo Shop • Thread closed")
    return embed


# ================== 3-OPTION DROPDOWN ==================

class XyooSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label="Video How To Order",
                value="tutorial",
                description="Watch our step-by-step ordering tutorial",
                emoji="🎥"
            ),
            discord.SelectOption(
                label="Payment Methods Available",
                value="payment_methods",
                description="View all accepted payment options",
                emoji="💳"
            ),
            discord.SelectOption(
                label="Order Here",
                value="order_here",
                description="Go to our website and place your order",
                emoji="🛍️"
            ),
        ]
        super().__init__(placeholder="Choose an option...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        selected = self.values[0]

        if selected == "tutorial":
            embed = get_tutorial_embed()
            await interaction.followup.send(embed=embed, ephemeral=True)
        elif selected == "payment_methods":
            embed = get_payment_methods_embed()
            await interaction.followup.send(embed=embed, ephemeral=True)
        elif selected == "order_here":
            embed = get_order_here_embed()
            await interaction.followup.send(embed=embed, ephemeral=True)


class SelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(XyooSelect())


# ================== /XYOO SETUP — CHANNEL PICKER ==================

class PanelChannelSelect(discord.ui.ChannelSelect):
    def __init__(self):
        super().__init__(
            placeholder="Choose a channel to post the Xyoo panel...",
            min_values=1,
            max_values=1,
            channel_types=[discord.ChannelType.text]
        )

    async def callback(self, interaction: discord.Interaction):
        try:
            channel = interaction.guild.get_channel(self.values[0].id)
            if not channel:
                await interaction.response.send_message("❌ Channel not found.", ephemeral=True)
                return

            bot.config["order_channel_id"] = channel.id
            save_config(bot.config)

            embed = get_main_embed()
            view = SelectView()
            await channel.send(embed=embed, view=view)

            logger.info(f"Panel posted in: {channel.name} ({channel.id})")
            await interaction.response.send_message(
                f"✅ **Panel posted in {channel.mention}!**\n"
                f"Customers can now use the dropdown there.\n"
                f"Order threads will also be created in that channel.\n\n"
                f"📌 To make this permanent across restarts, add `ORDER_CHANNEL_ID={channel.id}` to your Railway env.",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Panel setup error: {e}")
            await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)


class PanelSetupView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(PanelChannelSelect())


# ================== THREAD CLOSE HELPER ==================

async def close_thread_after_delay(thread: discord.Thread, seconds: int):
    try:
        await asyncio.sleep(1)
        msg = await thread.send(f"⏳ This thread will be closed in **{seconds}** seconds...")
        for i in range(seconds - 1, 0, -1):
            await asyncio.sleep(1)
            try:
                await msg.edit(content=f"⏳ This thread will be closed in **{i}** second{'s' if i != 1 else ''}...")
            except Exception:
                pass
        await asyncio.sleep(1)
        await thread.edit(archived=True, locked=True)
        logger.info(f"Thread {thread.id} closed")
    except Exception as e:
        logger.warning(f"Could not close thread {thread.id}: {e}")


# ================== VOUCH SYSTEM ==================

class VouchModal(discord.ui.Modal, title="⭐ Leave a Vouch"):
    vouch_message = discord.ui.TextInput(
        label="Your vouch message",
        placeholder="Tell others about your experience with Xyoo Shop!",
        style=discord.TextStyle.paragraph,
        max_length=500,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        vouch_channel_id = VOUCH_CHANNEL_ID if VOUCH_CHANNEL_ID != 0 else bot.config.get("vouch_channel_id")
        if not vouch_channel_id:
            await interaction.response.send_message("❌ Vouch channel not configured.", ephemeral=True)
            return
        vouch_channel = interaction.guild.get_channel(vouch_channel_id)
        if not vouch_channel:
            await interaction.response.send_message("❌ Vouch channel not found.", ephemeral=True)
            return

        embed = discord.Embed(
            title="⭐ New Vouch",
            description=self.vouch_message.value,
            color=GOLD_COLOR,
            timestamp=datetime.datetime.now()
        )
        embed.set_author(
            name=f"{interaction.user.display_name} (@{interaction.user.name})",
            icon_url=interaction.user.display_avatar.url
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.add_field(name="🆔 User ID", value=f"`{interaction.user.id}`", inline=True)
        embed.add_field(name="📌 Thread", value=interaction.channel.mention, inline=True)
        embed.set_footer(text="Xyoo Shop • Verified Purchase")
        await vouch_channel.send(embed=embed)

        await interaction.response.send_message(
            "✅ **Thank you for your vouch!** It has been posted.\n\n"
            "⏳ This thread will close in 5 seconds...",
            ephemeral=False
        )

        if isinstance(interaction.channel, discord.Thread):
            asyncio.create_task(close_thread_after_delay(interaction.channel, 5))


class VouchButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Leave a Vouch",
            style=discord.ButtonStyle.success,
            emoji="⭐"
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(VouchModal())


class VouchRequestView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(VouchButton())


# ================== SLASH COMMANDS ==================

@app_commands.command(name="ping", description="🏓 Ping the bot")
async def ping_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🏓 Pong!",
        description=f"Latency: **{bot.latency*1000:.0f}ms**",
        color=GREEN_COLOR
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


@app_commands.command(name="xyoo", description="[Admin] Post the Xyoo assistant panel in a channel")
@app_commands.default_permissions(administrator=True)
async def xyoo_command(interaction: discord.Interaction):
    view = PanelSetupView()
    embed = discord.Embed(
        title="🛠️ Xyoo Panel Setup",
        description="Choose which channel to post the assistant panel in:",
        color=EMBED_COLOR
    )
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


@app_commands.command(name="setup", description="[Admin] Reconfigure the order channel")
@app_commands.default_permissions(administrator=True)
async def setup_command(interaction: discord.Interaction):
    view = PanelSetupView()
    embed = discord.Embed(
        title="🛠️ Reconfigure Panel",
        description="Select a channel:",
        color=EMBED_COLOR
    )
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


@app_commands.command(name="request-vouch", description="[Admin] Ask customer to leave a vouch — auto-closes thread after")
@app_commands.default_permissions(administrator=True)
async def request_vouch_command(interaction: discord.Interaction):
    if not isinstance(interaction.channel, discord.Thread):
        await interaction.response.send_message(
            "❌ This command can only be used inside an order thread.", ephemeral=True
        )
        return

    embed = get_vouch_request_embed()
    view = VouchRequestView()
    await interaction.response.send_message(embed=embed, view=view)


@app_commands.command(name="close", description="[Admin] Close this thread without a vouch")
@app_commands.default_permissions(administrator=True)
async def close_command(interaction: discord.Interaction):
    if not isinstance(interaction.channel, discord.Thread):
        await interaction.response.send_message(
            "❌ This command can only be used inside a thread.", ephemeral=True
        )
        return

    embed = get_close_embed()
    await interaction.response.send_message(embed=embed)
    asyncio.create_task(close_thread_after_delay(interaction.channel, 5))


@bot.command(name="sync")
@commands.is_owner()
async def sync_commands(ctx):
    try:
        await bot.tree.sync()
        await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
        embed = discord.Embed(
            title="✅ Commands Synced!",
            description="All slash commands have been registered.",
            color=GREEN_COLOR
        )
        await ctx.send(embed=embed)
    except Exception as e:
        embed = discord.Embed(
            title="❌ Sync Failed",
            description=str(e),
            color=RED_COLOR
        )
        await ctx.send(embed=embed)


# ================== HELPER FUNCTIONS ==================

def find_member(guild, query):
    if not query:
        return None
    query = query.strip()
    if query.isdigit():
        member = guild.get_member(int(query))
        if member:
            logger.info(f"Found member by ID: {member.name}")
            return member
    query_lower = query.lower()
    for member in guild.members:
        if (
            member.name.lower() == query_lower
            or member.display_name.lower() == query_lower
            or (member.global_name and member.global_name.lower() == query_lower)
            or f"{member.name}#{member.discriminator}".lower() == query_lower
        ):
            logger.info(f"Exact match: {member.name}")
            return member
    for member in guild.members:
        if (
            query_lower in member.name.lower()
            or query_lower in member.display_name.lower()
            or (member.global_name and query_lower in member.global_name.lower())
        ):
            logger.info(f"Fuzzy match: {member.name}")
            return member
    logger.warning(f"No member found for: '{query}'")
    return None


async def process_order(order_data):
    try:
        await bot.wait_until_ready()
        guild = bot.get_guild(GUILD_ID)
        if not guild:
            logger.error(f"Guild {GUILD_ID} not found!")
            return None

        channel = None
        if ORDER_CHANNEL_ID and ORDER_CHANNEL_ID != 0:
            channel = guild.get_channel(ORDER_CHANNEL_ID)
        if not channel:
            config_id = bot.config.get("order_channel_id")
            if config_id:
                channel = guild.get_channel(config_id)
        if not channel:
            channel = discord.utils.get(guild.text_channels, name="orders")
        if not channel:
            channel = guild.text_channels[0]
        if not channel:
            logger.error("No suitable channel found!")
            return None

        thread_name = f"🛍️ ORDER - {order_data.get('orderId', 'Unknown')}"
        thread = await channel.create_thread(
            name=thread_name,
            type=discord.ChannelType.private_thread,
            auto_archive_duration=1440
        )
        logger.info(f"Private thread created: {thread.id} in {channel.name}")

        try:
            support_member = guild.get_member(SUPPORT_USER_ID)
            if support_member:
                await thread.add_user(support_member)
                logger.info("Support user added")
        except Exception as e:
            logger.warning(f"Could not add support user: {e}")

        customer_discord = order_data.get('discordUser', '').strip()
        customer_added = False
        member = None

        if customer_discord:
            logger.info(f"Looking for customer: '{customer_discord}'")
            member = find_member(guild, customer_discord)
            if member:
                try:
                    await channel.set_permissions(
                        member,
                        send_messages_in_threads=True,
                        read_messages=True
                    )
                    logger.info(f"Parent channel perms set for {member.name}")
                    await thread.add_user(member)
                    logger.info(f"Customer {member.name} added to thread")
                    customer_added = True
                except Exception as e:
                    logger.warning(f"Could not add customer {member.name}: {e}")
            else:
                logger.warning(f"Customer '{customer_discord}' not found in guild")
        else:
            logger.warning("No Discord username provided in order")

        embed = get_order_embed(order_data, customer_discord, customer_added, member)
        await thread.send(embed=embed)

        ping_msg = f"📢 **New order!** <@{SUPPORT_USER_ID}> please assist."
        if customer_discord:
            if customer_added:
                ping_msg += f"\n✅ Customer {member.mention} has been added to this private thread."
            else:
                ping_msg += f"\n⚠️ Customer `{customer_discord}` could not be added automatically."
                if member:
                    ping_msg += f"\n🔗 Mention: {member.mention} (please add manually)"
                else:
                    ping_msg += "\n🔗 They may not be in the server. Please invite them."
        await thread.send(ping_msg)

        return thread.id
    except Exception as e:
        logger.error(f"Process order error: {e}")
        return None


# ================== QUART ROUTES ==================

@app.route('/')
async def index():
    return await send_file('index.html')

@app.route('/payment-gcash.html')
async def gcash_page():
    return await send_file('payment-gcash.html')

@app.route('/payment-paypal.html')
async def paypal_page():
    return await send_file('payment-paypal.html')

@app.route('/payment-robux.html')
async def robux_page():
    return await send_file('payment-robux.html')

@app.route('/health')
async def health():
    return jsonify({"status": "ok"}), 200

@app.route('/api/order', methods=['POST'])
async def receive_order():
    api_key = request.headers.get('X-API-Key')
    if api_key != API_KEY:
        logger.warning("Unauthorized API request")
        return jsonify({"error": "Unauthorized"}), 401
    try:
        data = await request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON"}), 400
        logger.info(f"New order: {data.get('orderId')}")
        thread_id = await process_order(data)
        return jsonify({"status": "ok", "thread_id": str(thread_id) if thread_id else None}), 200
    except Exception as e:
        logger.error(f"Order processing error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/submit-code', methods=['POST'])
async def submit_code():
    api_key = request.headers.get('X-API-Key')
    if api_key != API_KEY:
        return jsonify({"error": "Unauthorized"}), 401
    try:
        data = await request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON"}), 400
        order_id = data.get('orderId')
        code = data.get('code')
        thread_id = data.get('threadId')
        if not order_id or not code:
            return jsonify({"error": "Missing orderId or code"}), 400
        logger.info(f"Robux code received for order {order_id}")
        if thread_id:
            guild = bot.get_guild(GUILD_ID)
            if guild:
                thread = guild.get_thread(int(thread_id))
                if thread:
                    embed = discord.Embed(
                        title="🎮 Robux Gift Card Code Submitted",
                        description=f"**Order ID:** `{order_id}`",
                        color=GREEN_COLOR,
                        timestamp=datetime.datetime.now()
                    )
                    embed.add_field(name="🔑 Gift Card Code", value=f"`{code}`", inline=False)
                    embed.set_footer(text="Xyoo Shop • Robux Payment")
                    await thread.send(embed=embed)
                    await thread.send(f"<@{SUPPORT_USER_ID}> Please redeem this code.")
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        logger.error(f"Submit code error: {e}")
        return jsonify({"error": str(e)}), 500


# ================== BOT EVENTS ==================

@bot.event
async def on_ready():
    logger.info(f"✅ Bot online as {bot.user}")


# ================== ENTRY POINT ==================

async def main():
    await app.run_task(host='0.0.0.0', port=PORT)

if __name__ == "__main__":
    if not DISCORD_TOKEN or not API_KEY:
        raise ValueError("Missing DISCORD_TOKEN or API_SECRET environment variables!")
    loop = asyncio.get_event_loop()
    loop.create_task(bot.start(DISCORD_TOKEN))
    loop.run_until_complete(main())