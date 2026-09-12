import discord
from discord.ext import commands
from discord import app_commands
import time

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

bot_admins = set()
bypass_whitelist = set()
blacklist = set()
stock = [] 
cooldowns = {} 

NORMAL_COOLDOWN = 1200      # 20 minutes for normal members
BOOSTER_COOLDOWN = 300      # Fast 5 minutes for whitelisted server boosters

# Variable to track the live stock message for auto-updates
stock_channel_id = None
stock_message_id = None

class AccountPanelView(discord.ui.View):
    def __init__(self): 
        super().__init__(timeout=None)

    @discord.ui.button(label="⚡ Generate Account", style=discord.ButtonStyle.primary, custom_id="persistent_account_generator_btn")
    async def generate_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await process_panel_generation(interaction)

@bot.event
async def on_ready():
    bot.add_view(AccountPanelView())
    await bot.tree.sync()
    print(f"✨ Logged in as {bot.user} successfully!")

def is_bot_admin(user: discord.Member) -> bool:
    return user.guild_permissions.administrator or user.id in bot_admins

def get_user_cooldown(member: discord.Member) -> int:
    if is_bot_admin(member):
        return 0
    is_booster = member.premium_since is not None
    if member.id in bypass_whitelist and is_booster:
        return BOOSTER_COOLDOWN
    return NORMAL_COOLDOWN

async def update_live_stock_display():
    global stock_channel_id, stock_message_id
    if stock_channel_id and stock_message_id:
        try:
            channel = bot.get_channel(stock_channel_id)
            if not channel:
                channel = await bot.fetch_channel(stock_channel_id)
            message = await channel.fetch_message(stock_message_id)
            
            embed = discord.Embed(
                title="📊 ┃ LIVE VAULT STOCK TRACKER",
                description=f"✨ **Current accounts available in stock:**\n\n🟢 **Available Stock:** `{len(stock)} accounts`\n\n📌 *This channel updates automatically every time new accounts are loaded!*",
                color=discord.Color.blurple()
            )
            await message.edit(embed=embed)
        except Exception as e:
            print(f"⚠️ Could not auto-update stock message: {e}")

# Free /generate command for ANY member (with normal cooldown)
async def process_account_generation(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)

    member = interaction.user
    if not isinstance(member, discord.Member):
        member = interaction.guild.get_member(interaction.user.id)

    if member.id in blacklist:
        embed = discord.Embed(title="⛔ ┃ Access Denied", description="❌ You are blacklisted from using this bot.", color=discord.Color.red())
        await interaction.followup.send(embed=embed, ephemeral=True)
        return

    cooldown_time = get_user_cooldown(member)
    
    if cooldown_time > 0:
        now = time.time()
        if member.id in cooldowns and now - cooldowns[member.id] < cooldown_time:
            remaining_sec = cooldown_time - (now - cooldowns[member.id])
            if remaining_sec >= 60:
                remaining_display = f"{round(remaining_sec / 60, 1)} minutes"
            else:
                remaining_display = f"{round(remaining_sec)} seconds"
                
            embed = discord.Embed(title="⏳ ┃ Cooldown Active", description=f"⌛ {member.mention}, please wait another **{remaining_display}** before generating another account.", color=discord.Color.orange())
            await interaction.channel.send(embed=embed)
            await interaction.delete_original_response()
            return
        cooldowns[member.id] = now

    if not stock:
        embed = discord.Embed(title="📦 ┃ Out of Stock", description="⚠️ There are currently **0** accounts available in stock. Please wait for a restock!", color=discord.Color.red())
        await interaction.followup.send(embed=embed, ephemeral=True)
        return

    email, password = stock.pop(0)
    
    await update_live_stock_display()

    try:
        dm = await member.create_dm()
        dm_embed = discord.Embed(
            title="🎉 ┃ Your Account Details",
            description=f"✨ **Here is your generated account:**\n\n📧 **Email:** `{email}`\n🔑 **Password:** `{password}`\n\nEnjoy your account! 🚀",
            color=discord.Color.green()
        )
        await dm.send(embed=dm_embed)
        
        embed = discord.Embed(title="✨ ┃ Generation Complete", description=f"✅ {member.mention} successfully generated an account! Check your Direct Messages 📥", color=discord.Color.green())
        await interaction.channel.send(embed=embed)
        await interaction.delete_original_response()
    except discord.Forbidden:
        stock.insert(0, (email, password))
        await update_live_stock_display() 
        embed = discord.Embed(title="⚠️ ┃ DM Error", description="❌ I couldn't send you a DM! Please open your Direct Messages and try again.", color=discord.Color.orange())
        await interaction.followup.send(embed=embed, ephemeral=True)

# Strict Booster-Only logic specifically for the /panel button
async def process_panel_generation(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)

    member = interaction.user
    if not isinstance(member, discord.Member):
        member = interaction.guild.get_member(interaction.user.id)

    if member.id in blacklist:
        embed = discord.Embed(title="⛔ ┃ Access Denied", description="❌ You are blacklisted from using this bot.", color=discord.Color.red())
        await interaction.followup.send(embed=embed, ephemeral=True)
        return

    is_admin = is_bot_admin(member)
    is_booster = member.premium_since is not None
    is_whitelisted = member.id in bypass_whitelist

    if not is_admin and not (is_whitelisted and is_booster):
        embed = discord.Embed(
            title="💎 ┃ Booster & Whitelist Only", 
            description="❌ Sorry! This panel is only for whitelisted server boosters. Please boost the server and get whitelisted by an admin to use this.", 
            color=discord.Color.orange()
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
        return

    # Use the same generation logic once verified as booster/whitelisted
    await process_panel_allowed_generation(interaction, member)

async def process_panel_allowed_generation(interaction: discord.Interaction, member: discord.Member):
    cooldown_time = get_user_cooldown(member)
    
    if cooldown_time > 0:
        now = time.time()
        if member.id in cooldowns and now - cooldowns[member.id] < cooldown_time:
            remaining_sec = cooldown_time - (now - cooldowns[member.id])
            if remaining_sec >= 60:
                remaining_display = f"{round(remaining_sec / 60, 1)} minutes"
            else:
                remaining_display = f"{round(remaining_sec)} seconds"
                
            embed = discord.Embed(title="⏳ ┃ Cooldown Active", description=f"⌛ {member.mention}, please wait another **{remaining_display}** before generating another account.", color=discord.Color.orange())
            await interaction.channel.send(embed=embed)
            await interaction.delete_original_response()
            return
        cooldowns[member.id] = now

    if not stock:
        embed = discord.Embed(title="📦 ┃ Out of Stock", description="⚠️ There are currently **0** accounts available in stock. Please wait for a restock!", color=discord.Color.red())
        await interaction.followup.send(embed=embed, ephemeral=True)
        return

    email, password = stock.pop(0)
    
    await update_live_stock_display()

    try:
        dm = await member.create_dm()
        dm_embed = discord.Embed(
            title="🎉 ┃ Your Account Details",
            description=f"✨ **Here is your generated account:**\n\n📧 **Email:** `{email}`\n🔑 **Password:** `{password}`\n\nEnjoy your account! 🚀",
            color=discord.Color.green()
        )
        await dm.send(embed=dm_embed)
        
        embed = discord.Embed(title="✨ ┃ Generation Complete", description=f"✅ {member.mention} successfully generated an account! Check your Direct Messages 📥", color=discord.Color.green())
        await interaction.channel.send(embed=embed)
        await interaction.delete_original_response()
    except discord.Forbidden:
        stock.insert(0, (email, password))
        await update_live_stock_display() 
        embed = discord.Embed(title="⚠️ ┃ DM Error", description="❌ I couldn't send you a DM! Please open your Direct Messages and try again.", color=discord.Color.orange())
        await interaction.followup.send(embed=embed, ephemeral=True)

admin_group = app_commands.Group(name="admin", description="Manage bot admins.")

@admin_group.command(name="add", description="Add bot admin.")
async def admin_add(interaction: discord.Interaction, user: discord.Member):
    if not interaction.user.guild_permissions.administrator:
        embed = discord.Embed(title="⛔ ┃ Permission Denied", description="🔒 Server administrators only!", color=discord.Color.red())
        return await interaction.response.send_message(embed=embed, ephemeral=True)
    bot_admins.add(user.id)
    embed = discord.Embed(title="✅ ┃ Admin Added", description=f"Successfully added {user.mention} as a bot admin! 🛡️", color=discord.Color.green())
    await interaction.response.send_message(embed=embed, ephemeral=True)

@admin_group.command(name="remove", description="Remove bot admin.")
async def admin_remove(interaction: discord.Interaction, user: discord.Member):
    if not interaction.user.guild_permissions.administrator:
        embed = discord.Embed(title="⛔ ┃ Permission Denied", description="🔒 Server administrators only!", color=discord.Color.red())
        return await interaction.response.send_message(embed=embed, ephemeral=True)
    bot_admins.discard(user.id)
    embed = discord.Embed(title="❌ ┃ Admin Removed", description=f"Removed {user.mention} from bot admins.", color=discord.Color.red())
    await interaction.response.send_message(embed=embed, ephemeral=True)

bot.tree.add_command(admin_group)

@bot.tree.command(name="whitelist", description="Whitelist user.")
async def whitelist_user(interaction: discord.Interaction, user: discord.Member):
    if not is_bot_admin(interaction.user): 
        embed = discord.Embed(title="⛔ ┃ Permission Denied", description="❌ You do not have permission to use this command.", color=discord.Color.red())
        return await interaction.response.send_message(embed=embed, ephemeral=True)
    bypass_whitelist.add(user.id)
    embed = discord.Embed(title="✅ ┃ Whitelisted", description=f"✨ Successfully whitelisted {user.mention} for booster generator access (5-minute cooldown)!", color=discord.Color.green())
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="unwhitelist", description="Unwhitelist user.")
async def unwhitelist_user(interaction: discord.Interaction, user: discord.Member):
    if not is_bot_admin(interaction.user): 
        embed = discord.Embed(title="⛔ ┃ Permission Denied", description="❌ You do not have permission to use this command.", color=discord.Color.red())
        return await interaction.response.send_message(embed=embed, ephemeral=True)
    bypass_whitelist.discard(user.id)
    embed = discord.Embed(title="❌ ┃ Unwhitelisted", description=f"Removed {user.mention} from the whitelist.", color=discord.Color.orange())
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="whitelist-list", description="Check who is currently whitelisted.")
async def whitelist_list(interaction: discord.Interaction):
    if not is_bot_admin(interaction.user): 
        embed = discord.Embed(title="⛔ ┃ Permission Denied", description="❌ You do not have permission to use this command.", color=discord.Color.red())
        return await interaction.response.send_message(embed=embed, ephemeral=True)
    
    if not bypass_whitelist:
        embed = discord.Embed(title="📋 ┃ Whitelist Roster", description="⚠️ There are currently **0** users on the whitelist.", color=discord.Color.orange())
    else:
        mentions = [f"<@{uid}>" for uid in bypass_whitelist]
        embed = discord.Embed(title="📋 ┃ Whitelisted Users", description="✨ **Here are the currently whitelisted members:**\n\n" + "\n".join(mentions), color=discord.Color.blurple())
        
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="blacklist", description="Blacklist user.")
async def blacklist_user(interaction: discord.Interaction, user: discord.Member):
    if not is_bot_admin(interaction.user): 
        embed = discord.Embed(title="⛔ ┃ Permission Denied", description="❌ You do not have permission to use this command.", color=discord.Color.red())
        return await interaction.response.send_message(embed=embed, ephemeral=True)
    blacklist.add(user.id)
    embed = discord.Embed(title="⛔ ┃ Blacklisted", description=f"🚫 Blacklisted {user.mention} from using bot commands.", color=discord.Color.red())
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="unblacklist", description="Unblacklist user.")
async def unblacklist_user(interaction: discord.Interaction, user: discord.Member):
    if not is_bot_admin(interaction.user): 
        embed = discord.Embed(title="⛔ ┃ Permission Denied", description="❌ You do not have permission to use this command.", color=discord.Color.red())
        return await interaction.response.send_message(embed=embed, ephemeral=True)
    blacklist.discard(user.id)
    embed = discord.Embed(title="✅ ┃ Unblacklisted", description=f"✨ Unblacklisted {user.mention}.", color=discord.Color.green())
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="remove-time", description="Reset a user's cooldown timer if they received a bad account.")
async def remove_time(interaction: discord.Interaction, user: discord.Member):
    if not is_bot_admin(interaction.user): 
        embed = discord.Embed(title="⛔ ┃ Permission Denied", description="❌ You do not have permission to use this command.", color=discord.Color.red())
        return await interaction.response.send_message(embed=embed, ephemeral=True)
    
    if user.id in cooldowns:
        del cooldowns[user.id]
        
    embed = discord.Embed(
        title="⏱️ ┃ Cooldown Reset", 
        description=f"✅ Successfully cleared the cooldown timer for {user.mention}! They can now generate a new account.", 
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="restock", description="Add account to stock.")
async def restock(interaction: discord.Interaction, email: str, password: str):
    if not is_bot_admin(interaction.user): 
        embed = discord.Embed(title="⛔ ┃ Permission Denied", description="❌ You do not have permission to use this command.", color=discord.Color.red())
        return await interaction.response.send_message(embed=embed, ephemeral=True)
    
    stock.append((email, password))
    await update_live_stock_display()

    embed = discord.Embed(title="📦 ┃ Restock Successful", description=f"✅ Successfully added 1 account to stock!\n📈 **Total Stock:** `{len(stock)} accounts`", color=discord.Color.blue())
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="setup-stock", description="Set up the live auto-updating stock tracker channel.")
async def setup_stock(interaction: discord.Interaction):
    global stock_channel_id, stock_message_id
    if not is_bot_admin(interaction.user): 
        embed = discord.Embed(title="⛔ ┃ Permission Denied", description="🔒 Server administrators only!", color=discord.Color.red())
        return await interaction.response.send_message(embed=embed, ephemeral=True)

    stock_channel_id = interaction.channel.id
    
    embed = discord.Embed(
        title="📊 ┃ LIVE VAULT STOCK TRACKER",
        description=f"✨ **Current accounts available in stock:**\n\n🟢 **Available Stock:** `{len(stock)} accounts`\n\n📌 *This channel updates automatically every time new accounts are loaded!*",
        color=discord.Color.blurple()
    )
    
    msg = await interaction.channel.send(embed=embed)
    stock_message_id = msg.id

    success_embed = discord.Embed(title="✅ ┃ Stock Tracker Setup", description="🎉 This channel has been successfully linked as the live stock display!", color=discord.Color.green())
    await interaction.response.send_message(success_embed, ephemeral=True)

# /generate is free for everyone to use (with cooldowns)
@bot.tree.command(name="generate", description="Generate an account.")
async def generate(interaction: discord.Interaction):
    await process_account_generation(interaction)

@bot.tree.command(name="stock", description="Check stock.")
async def stock_command(interaction: discord.Interaction):
    embed = discord.Embed(title="📦 ┃ Server Stock Status", description=f"🟢 There are currently **{len(stock)}** accounts available in stock!", color=discord.Color.blurple())
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="panel", description="Post generator panel.")
async def panel_command(interaction: discord.Interaction):
    if not is_bot_admin(interaction.user): 
        embed = discord.Embed(title="⛔ ┃ Permission Denied", description="❌ You do not have permission to use this command.", color=discord.Color.red())
        return await interaction.response.send_message(embed=embed, ephemeral=True)
    
    panel_embed = discord.Embed(
        title="⚡ ┃ VAULT 404 — Server Booster Generator",
        description="✨ **Welcome to the official booster drop center!**\n\nClick the button below to instantly claim your verified account straight to your Direct Messages. *(Requires Server Boost & Whitelist)*\n\n🟢 **Status:** `Online & Ready`",
        color=discord.Color.blurple()
    )
    panel_embed.set_footer(text="Vault 404 • Secure Automated Delivery")
    
    view = AccountPanelView()
    await interaction.channel.send(embed=panel_embed, view=view)
    embed = discord.Embed(title="✅ ┃ Panel Deployed", description="🚀 The booster-only generator panel has been successfully posted!", color=discord.Color.green())
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="help", description="View the help menu.")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📖 ┃ Help Menu",
        description="✨ **Available Commands:**\n\n• `/generate` - Free command for members (20 min cooldown, 5 min for boosters)\n• `/stock` - Check current stock\n• `/help` - View this help menu",
        color=discord.Color.blurple()
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

bot.run("")
      
