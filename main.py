import discord
from discord import ui, app_commands
import json
from discord.ext.commands.converter import PartialMessageConverter
from config import *
import chat_exporter
import io
import asyncio
import threading
from webserver import app
import canvacord
import random
from colour import Color


class Client(discord.Client):
  def __init__(self):
    intents = discord.Intents.all()
    activity = discord.CustomActivity("Look at me!")
    super().__init__(intents=intents, activity=activity)
    self.tree = app_commands.CommandTree(self)
  async def on_ready(self):
    print("Logged in as {0.user}".format(self))
    await self.tree.sync()
  async def setup_hook(self):
    ticketsystem = app_commands.Group(name='tickets', description='Ticket commands')
    ticketsystem.add_command(app_commands.Command(name = "setup", description="Setup the ticket system", callback = ticketsystem_setup_command))
    ticketsystem.add_command(app_commands.Command(name = "resend", description="Send a specific ticket panel again", callback = ticketsystem_resend_command))
    ticketsystem.add_command(app_commands.Command(name = "delete", description="Delete a specific ticket panel", callback = ticketsystem_delete_command))
    
    self.tree.add_command(ticketsystem)

    xpsystem = app_commands.Group(name='xp', description='XP/Leveling commands')
    xpsystem.add_command(app_commands.Command(name = "setup", description = "Setup the xp/leveling system", callback = xpsystemsetup))
    xpsystem.add_command(app_commands.Command(name = 'rank', description = "Get your current rank card", callback = xpsystemrankcard))
    xpsystem.add_command(app_commands.Command(name = 'leaderboard', description = 'Display the current xp/leveling leaderboard', callback = xpsystemleaderboard))

    self.tree.add_command(xpsystem)

    announcements = app_commands.Group(name='announcements', description = 'Announcements for join, leave and ban')
    announcements_add = app_commands.Command(name = 'add', description = 'Add a new announcement', callback = announcements_add_join)
    announcements_remove = app_commands.Command(name = 'remove', description = 'Remove an announcement', callback = announcements_remove_join)
    announcements.add_command(announcements_remove)
    announcements.add_command(announcements_add)

    self.tree.add_command(announcements)


    # test = app_commands.Group(name='test', description='Currently in test')
    # test.add_command(app_commands.Command(name = 'rank', description = 'Display your rank card', callback = testRankCard))
    
    # self.tree.add_command(test)

client = Client()

@client.tree.command(name="say")
async def say_command(interaction, text: str = None):
  """Let Demon say something

  Parameters
  ----------
  text : str
      Text to say"""
  await interaction.response.defer()
  if text:
    await interaction.followup.send("You said: "+text)
  else:
    await interaction.followup.send("You said nothing.")

async def ticketsystem_setup_command(interaction, name: str, panel :discord.TextChannel, category: discord.CategoryChannel = None, mention: discord.Role = None):
  """Setup the Ticket system

  Parameters
  ----------
  name : str
      A unique name for your tickets panel.
  mention : discord.Role
      Mention your everyone role [@everyone]
  panel : discord.TextChannel
      The channel where the ticket panel will appear
  category : discord.CategoryChannel
      The category where the tickets go in."""
  await interaction.response.defer(ephemeral = True)
  server_name = interaction.guild.name
  ticketpanels = json.loads(open('ticketpanels.json', 'r').read())
  staff = json.loads(open('staff.json', 'r').read())
  if not interaction.guild:
    embed = discord.Embed(title="Ticket system", description="This command can only be used in a server!", color = embed_color_error)
    await interaction.followup.send(embed = embed)
    return
  isStaff = False
  member = interaction.guild.get_member(interaction.user.id)
  if str(interaction.guild.id) in staff:
    for role in member.roles:
      if role.id in staff["manager"]:
        isStaff = True
  if member.guild_permissions.administrator or member.id == interaction.guild.owner.id:
    isStaff = True
  if not isStaff:
    embed = discord.Embed(title="Ticket system", description="You don't have permission to use this command!", color = embed_color_error)
    await interaction.followup.send(embed = embed)
    return
  if str(interaction.guild.id) + '-' + name in ticketpanels:
    embed = discord.Embed(title="Ticket system", description="This ticket panel already exists!", color = embed_color_error)
    await interaction.followup.send(embed = embed)
    return
  ticketpanels[str(interaction.guild.id) + '-' + name] = {
    "name": name,
    "guild_id": interaction.guild.id,
    "category_id": category.id if category else None,
    "message_id": None,
    "description": "This is the ticket support of {server}.",
    "title": "{server} Support",
    "welcome_message": "Thanks for contacting {server} support.\nWe will be here for you shortly.",
    "button_label": "🎟️ Create a Ticket",
  }
  open('ticketpanels.json', 'w').write(json.dumps(ticketpanels, indent = 4))
  class ConfirmAndViewView(ui.View):
    def __init__(self, guild_id, panel_name, mention, panel):
      super().__init__(timeout = None)
      self.guild_id = guild_id
      self.panel_name = panel_name
      self.mention = mention
      self.panel = panel
    @ui.button(label = "Send panel", style = discord.ButtonStyle.green)
    async def send_panel(self, interaction, button):
      await interaction.response.defer(ephemeral = True)
      guild = client.get_guild(self.guild_id)
      panel = ticketpanels[str(self.guild_id) + '-' + self.panel_name]
      embed = discord.Embed(title = panel["title"].replace("{server}", guild.name), description = panel["description"].replace("{server}", guild.name), color = embed_color)
      embed.set_footer(text = f"Click the button below to open a ticket")
      button = discord.ui.Button(label = panel["button_label"], style = discord.ButtonStyle.blurple, custom_id = "create_ticket_"+panel["name"])
      view = ui.View()
      view.add_item(button)
      if self.panel:
        try:
          if self.mention:
            await self.panel.send(content = self.mention.mention, embed = embed, view = view)
          else:
            await self.panel.send(embed = embed, view = view)
        except:
          embed = discord.Embed(title = "Ticket system", description = "I don't have permission to send messages in <#"+str(self.panel.channel.id)+">!", color = embed_color_error)
          await interaction.followup.send(embed = embed)
      else:
        try:
          if self.mention:
            await interaction.channel.send(content = self.mention.mention, embed = embed, view = view)
          else:
            await interaction.channel.send(embed = embed, view = view)
        except:
          embed = discord.Embed(title = "Ticket system", description = "I don't have permission to send messages in this channel!", color = embed_color_error)
          await interaction.followup.send(embed = embed)
    @ui.button(label = "Preview", style = discord.ButtonStyle.red)
    async def preview(self, interaction, button):
      await interaction.response.defer(ephemeral = True)
      guild = client.get_guild(self.guild_id)
      panel = ticketpanels[str(self.guild_id) + '-' + self.panel_name]
      embed = discord.Embed(title = panel["title"].replace("{server}", guild.name), description = panel["description"].replace("{server}", guild.name), color = embed_color)
      embed.set_footer(text = f"Click the button below to open a ticket")
      button = discord.ui.Button(label = panel["button_label"], style = discord.ButtonStyle.blurple, custom_id = "create_ticket_"+panel["name"], disabled = True)
      view = ui.View()
      view.add_item(button)
      if self.mention:
        await interaction.followup.send(content = self.mention.mention, embed = embed, view = view, ephemeral = True)
      else:
        await interaction.followup.send(embed = embed, view = view, ephemeral = True)
      
  embed = discord.Embed(title="Ticket system", description="Tickets have been setup!", color=embed_color_success)
  await interaction.followup.send(embed = embed, view=ConfirmAndViewView(guild_id = interaction.guild.id, panel_name = name, mention = mention, panel = panel))

async def complete_ticketsystem_panelname(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
  ticketpanels = json.loads(open('ticketpanels.json', 'r').read())
  guild_id = interaction.guild.id
  return [app_commands.Choice(name = panel["name"], value = panel["name"]) for panel in ticketpanels.values() if panel["guild_id"] == guild_id and panel["name"].startswith(current)]

@app_commands.autocomplete(name = complete_ticketsystem_panelname)
async def ticketsystem_resend_command(interaction, name: str, channel: discord.TextChannel, mention: discord.Role = None):
  """Send a specific ticket panel again
  Parameters
  ----------
  name : str
      A unique name for your tickets panel.
  mention : discord.Role
      Mention your everyone role [@everyone]
  channel : discord.TextChannel
      The channel where the ticket panel will appear"""
  await interaction.response.defer(ephemeral = True)
  ticketpanels = json.loads(open('ticketpanels.json', 'r').read())
  staff = json.loads(open('staff.json', 'r').read())
  if not interaction.guild:
    embed = discord.Embed(title="Ticket system", description="This command can only be used in a server!", color = embed_color_error)
    await interaction.followup.send(embed = embed)
    return
  isStaff = False
  if str(interaction.guild.id) in staff:
    member = interaction.guild.get_member(interaction.user.id)
    if member.guild_permissions.administrator or member.id == interaction.guild.owner.id:
      isStaff = True
    else:
      for role in member.roles:
        if role.id in staff["manager"]:
          isStaff = True
  if not isStaff:
    embed = discord.Embed(title="Ticket system", description="You don't have permission to use this command!", color = embed_color_error)
    await interaction.followup.send(embed = embed)
    return
  guild = interaction.guild
  try:
    panel = ticketpanels[str(guild.id) + '-' + name]
  except:
    embed = discord.Embed(title = "Ticket system", description = "This ticket panel doesn't exist!", color = embed_color_error)
    await interaction.followup.send(embed = embed)
    return
  embed = discord.Embed(title = panel["title"].replace("{server}", guild.name), description = panel["description"].replace("{server}", guild.name), color = embed_color)
  embed.set_footer(text = f"Click the button below to open a ticket")
  button = discord.ui.Button(label = panel["button_label"], style = discord.ButtonStyle.blurple, custom_id = "create_ticket_"+panel["name"])
  view = ui.View()
  view.add_item(button)
  if channel:
    try:
      if mention:
        await channel.send(content = mention.mention, embed = embed, view = view)
        await interaction.followup.send('Sent')
      else:
        await channel.send(embed = embed, view = view)
        await interaction.followup.send('Sent')
    except:
      embed = discord.Embed(title = "Ticket system", description = "I don't have permission to send messages in <#"+str(channel.id)+">!", color = embed_color_error)
      await interaction.followup.send(embed = embed)
  else:
    try:
      if mention:
        await interaction.channel.send(content = mention.mention, embed = embed, view = view, ephemeral = True)
        await interaction.followup.send('Sent')
      else:
        await interaction.channel.send(embed = embed, view = view, ephemeral = True)
        await interaction.followup.send('Sent')
    except:
      embed = discord.Embed(title = "Ticket system", description = "I don't have permission to send messages in this channel!", color = embed_color_error)
      await interaction.followup.send(embed = embed)

@app_commands.autocomplete(name = complete_ticketsystem_panelname)
async def ticketsystem_delete_command(interaction, name: str):
  """Delete a specific ticket panel

  Parameters
  ----------
  name : str
    A unique name for your tickets panel.
  """
  await interaction.response.defer(ephemeral = True)
  ticketpanels = json.loads(open('ticketpanels.json', 'r').read())
  staff = json.loads(open('staff.json', 'r').read())
  if not interaction.guild:
    embed = discord.Embed(title="Ticket system", description="This command can only be used in a server!", color = embed_color_error)
    await interaction.followup.send(embed = embed)
    return
  isStaff = False
  if str(interaction.guild.id) in staff:
    member = interaction.guild.get_member(interaction.user.id)
    if member.guild_permissions.administrator or member.id == interaction.guild.owner.id:
      isStaff = True
    else:
      for role in member.roles:
        if role.id in staff["manager"]:
          isStaff = True
  if not isStaff:
    embed = discord.Embed(title="Ticket system", description="You don't have permission to use this command!", color = embed_color_error)
    await interaction.followup.send(embed = embed)
    return
  guild = interaction.guild
  try:
    panel = ticketpanels[str(guild.id) + '-' + name]
  except:
    embed = discord.Embed(title = "Ticket system", description = "This ticket panel doesn't exist!", color = embed_color_error)
    await interaction.followup.send(embed = embed)
    return
  view = ui.View()
  button = discord.ui.Button(label = "Yes", style = discord.ButtonStyle.red, custom_id = "delete_ticket_panel_"+panel["name"])
  view.add_item(button)
  embed = discord.Embed(title = "Ticket system", description = "Are you sure you want to delete this ticket panel?", color = embed_color_warning)
  await interaction.followup.send(embed = embed, view = view)
  # wait for new button press
  try:
    interaction = await client.wait_for("interaction", check = lambda i: i.data['custom_id'] == "delete_ticket_panel_"+panel["name"], timeout = 120)
    await interaction.response.defer(ephemeral = True)
    await interaction.followup.send(content = "Deleting ticket panel...", ephemeral = True)
    del ticketpanels[str(guild.id) + '-' + name]
    json.dump(ticketpanels, open('ticketpanels.json', 'w'), indent = 4)
    embed = discord.Embed(title = "Ticket system", description = "The ticket panel `"+name+"` has been deleted!", color = embed_color_success)
    embed.set_footer(text="You'd have to delete the panel message yourself.")
    await interaction.followup.send(embed = embed, ephemeral= True)
  except Exception as es:
    print(es)
    embed = discord.Embed(title = "Ticket system", description = "You took too long to respond!", color = embed_color_error)
    await interaction.followup.send(embed = embed, ephemeral = True)


@client.event
async def on_interaction(interaction):
  if interaction.type == discord.InteractionType.component:
    if interaction.data['custom_id'].startswith("create_ticket_"):
      await interaction.response.defer(ephemeral = True)
      ticketpanels = json.loads(open('ticketpanels.json', 'r').read())
      staff = json.loads(open('staff.json', 'r').read())
      guild = interaction.guild
      try:
        panel = ticketpanels[str(guild.id) + '-' + interaction.data['custom_id'].split('_')[2]]
      except:
        embed = discord.Embed(title = "Ticket system", description = "This ticket panel doesn't exist!", color = embed_color_error)
        await interaction.followup.send(embed = embed, ephemeral = True)
        return
      for channel in interaction.guild.channels:
        if channel.name == interaction.user.name:
          embed = discord.Embed(title = "Ticket system", description = "You already have a ticket open in this server!", color = embed_color_error)
          await interaction.followup.send(embed = embed, ephemeral = True)
          return
      channel = None
      if panel["category_id"]:
        category = guild.get_channel(panel["category_id"])
        if category:
          channel = await category.create_text_channel(name = interaction.user.name, topic = interaction.user.id, overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages = False),
            interaction.user: discord.PermissionOverwrite(read_messages = True, send_messages = True, embed_links = True, attach_files = True, add_reactions = True, read_message_history = True),
            guild.me: discord.PermissionOverwrite(read_messages = True, send_messages = True, embed_links = True, attach_files = True, add_reactions = True, read_message_history = True)
          })
      if not channel:
        channel = await guild.create_text_channel(name = interaction.user.name, topic = interaction.user.id, overwrites = {
          guild.default_role: discord.PermissionOverwrite(read_messages = False),
          interaction.user: discord.PermissionOverwrite(read_messages = True, send_messages = True, embed_links = True, attach_files = True, add_reactions = True, read_message_history = True),
          guild.me: discord.PermissionOverwrite(read_messages = True, send_messages = True, embed_links = True, attach_files = True, add_reactions = True, read_message_history = True),
        })
      # add all staffs to ticket
      if str(interaction.guild.id) in staff:
        staff = staff[str(interaction.guild.id)]
        moderator_roles = staff['moderator']
        manager_roles = staff['manager']
        supporter_roles = staff['supporter']
        for role in interaction.guild.roles:
          if role.id in moderator_roles or role.id in manager_roles or role.id in supporter_roles:
            await channel.set_permissions(role, read_messages = True, send_messages = True, embed_links = True, attach_files = True, add_reactions = True, read_message_history = True)
      embed = discord.Embed(title = "Ticket system", description = "Your ticket has been created!", color = embed_color_success)
      await interaction.followup.send(embed = embed, ephemeral = True)
      ticket_embed = discord.Embed(title = panel["title"].replace("{server}", guild.name), description = panel["welcome_message"].replace("{server}", guild.name), color = embed_color)
      ticket_embed.set_footer(text= "Close the ticket by pressing the button below")
      try:
        ticket_embed.set_thumnail(url = interaction.guild.icon.url)
      except:
        pass
      view = ui.View()
      view.add_item(ui.Button(label = "Close Ticket", style = discord.ButtonStyle.red, custom_id = "close_ticket"))
      await channel.send(embed = ticket_embed, view = view)
    if interaction.data['custom_id'] == "close_ticket":
      await interaction.response.defer()
      staff = json.loads(open('staff.json', 'r').read())
      if str(interaction.guild.id) in staff:
        staff = staff[str(interaction.guild.id)]
        moderator_roles = staff['moderator']
        manager_roles = staff['manager']
        supporter_roles = staff['supporter']
      else:
        moderator_roles = []
        manager_roles = []
        supporter_roles = []
      member = interaction.guild.get_member(interaction.user.id)
      userid = None
      try:
        userid = int(interaction.channel.topic)
      except:
        pass
      for role in member.roles:
        if role.id in moderator_roles or role.id in manager_roles or member.guild_permissions.administrator or member.id == interaction.guild.owner.id or member.id == userid:
          # Do you really want to close this ticket? this can't be undone. (do with on_interaction and client.wait_for)
          embed = discord.Embed(title = "Are you sure?", description = "Are you sure you want to close this ticket?", color = embed_color_warning)
          view = ui.View()
          view.add_item(ui.Button(label = "Yes", style = discord.ButtonStyle.green, custom_id = "close_ticket_yes"))
          view.add_item(ui.Button(label = "No", style = discord.ButtonStyle.red, custom_id = "close_ticket_no"))
          await interaction.followup.send(embed = embed, view = view)
          close_ticket_interaction = await client.wait_for("interaction", check = lambda i: i.user.id == interaction.user.id and i.channel.id == interaction.channel.id and i.data["custom_id"] in ["close_ticket_yes", "close_ticket_no"])
          await close_ticket_interaction.response.defer(ephemeral = True)
          await close_ticket_interaction.message.delete()
          if close_ticket_interaction.data['custom_id'] == "close_ticket_yes":
            transcript = await chat_exporter.export(interaction.channel)
            link = None
            if transcript:
              transcript_file = discord.File(
                io.BytesIO(transcript.encode()),
                filename = f"transcript-{interaction.channel.name}.html",
              )
              for guild in client.guilds:
                if guild.id == support_server_id:
                  for channel in guild.channels:
                    if channel.id == channel_for_tickets:
                      message = await channel.send(file = transcript_file)
              link = await chat_exporter.link(message)
            msg = await interaction.followup.send(content = "Ticket will be closed in 5 seconds", ephemeral = True)
            await asyncio.sleep(5)
            for role in supporter_roles:
              await interaction.channel.set_permissions(interaction.guild.get_role(role), read_messages = False, send_messages = False, embed_links = False, attach_files = False, add_reactions = False, read_message_history = False)
            await interaction.channel.edit(name='closed-'+interaction.channel.name)
            view = ui.View()
            view.add_item(ui.Button(label = "Delete Ticket", style = discord.ButtonStyle.red, custom_id = "delete_ticket"))
            await interaction.message.edit(view=view)
            embed = discord.Embed(title = "Ticket system", description = "Ticket has been closed!", color = embed_color)
            embed.add_field(name = "Closed by", value = f"{member.name}")
            if link:
              embed.add_field(name = "View transcript", value = f"[Click here]({link})")
            await msg.delete()
            await interaction.channel.send(embed = embed)
            try:
              user = await client.fetch_user(int(interaction.channel.topic))
              member_of_user = interaction.guild.get_member(user.id)
              await interaction.channel.set_permissions(member_of_user, read_messages = False, send_messages = False, embed_links = False, attach_files = False, add_reactions = False, read_message_history = False)
              if user.id == member.id:
                embed = discord.Embed(title = "Ticket system", description = "Your ticket has been closed!", color = embed_color_success)
                if link:
                  embed.add_field(name = "View transcript", value = f"[Click here]({link})")
                await user.send(embed = embed)
              else:
                embed = discord.Embed(title = "Ticket system", description = "Your ticket in {} has been closed!".format(guild.name), color = embed_color_success)
                embed.add_field(name = "Closed by", value = f"{member.name}")
                if link:
                  embed.add_field(name = "View transcript", value = f"[Click here]({link})")
                
                await user.send(embed = embed)
            except:
              pass
                
            return
          else:
            await interaction.followup.send(content = "Ticket will not be closed", ephemeral = True)
            return
        else:
          await interaction.followup.send(content = "You don't have permission to close this ticket!", ephemeral = True)
          return
    if interaction.data['custom_id'] == "delete_ticket":
      await interaction.response.defer()
      embed = discord.Embed(title = "Ticket system", description = "Are you sure you want to delete this ticket?", color = embed_color_warning)
      view = ui.View()
      view.add_item(ui.Button(label = "Yes", style = discord.ButtonStyle.red, custom_id = "delete_ticket_yes"))
      view.add_item(ui.Button(label = "No", style = discord.ButtonStyle.gray, custom_id = "delete_ticket_no"))
      await interaction.followup.send(embed = embed, view = view)
      return
    if interaction.data['custom_id'] == "delete_ticket_yes":
      await interaction.response.defer(ephemeral= True)
      embed = discord.Embed(title = "Ticket system", description = "Ticket will be deleted in 5 seconds", color = embed_color)
      await interaction.followup.send(embed = embed)
      await asyncio.sleep(5)
      await interaction.channel.delete()
      return
    if interaction.data['custom_id'] == "delete_ticket_no":
      await interaction.response.defer(ephemeral= True)
      await interaction.message.delete()
      await interaction.followup.send(content = "Ticket deletion cancelled", ephemeral = True)

@client.event
async def on_message(message):
  if message.author.bot:
    return
  if message.guild:
    try:
      xpsettings = json.loads(open('xpranks/'+str(message.guild.id) + '-settings.json', 'r').read())
    except Exception as es:
      print(es)
      xpsettings = None
    if xpsettings:
      if xpsettings['enabled']:
        try:
          serverxp = json.loads(open('xpranks/'+str(message.guild.id)+'-users.json', 'r').read())
        except:
          serverxp = {}
        if not str(message.author.id) in serverxp.keys():
          serverxp[str(message.author.id)] = {
            "currentxp": 0,
            "currentlevel": 1,
          }
        serverxp[str(message.author.id)]["currentxp"] += xpsettings["xppermessage"]
        neededxp = xpsettings["firstlevelxp"] + (serverxp[str(message.author.id)]["currentlevel"] - 1) * xpsettings["xplevelincrement"]
        json.dump(serverxp, open('xpranks/'+str(message.guild.id) + '-users.json', 'w'), indent = 4)
        if serverxp[str(message.author.id)]["currentxp"] == neededxp:
          serverxp[str(message.author.id)]["currentlevel"] += 1
          serverxp[str(message.author.id)]["currentxp"] = 0
          json.dump(serverxp, open('xpranks/'+str(message.guild.id) + '-users.json', 'w'), indent = 4)
          if xpsettings["dolevelupmessage"]:
            channel = None
            if xpsettings["levelupchannel"]:
              for channelnum in message.guild.channels:
                if channelnum.id == xpsettings["levelupchannel"]:
                  channel = channelnum
            if not channel:
              channel = message.channel
            if xpsettings["levelupmessagetype"] == 'embed':
              embed = discord.Embed(title = message.author.name + " reached level "+str(serverxp[str(message.author.id)]["currentlevel"]),
                                    description = "Cheers 🎉🎊", color = embed_color_premium)
              try:
                await channel.send(embed = embed)
              except:
                pass
            else:
              try:
                await channel.send(message.author.name + " reached level "+str(serverxp[str(message.author.id)]["currentlevel"]))
              except:
                pass



async def xpsystemsetup(interaction, enabled: bool = True):
  await interaction.response.defer(ephemeral= True)
  try:
    xpsettings = json.loads(open('xpranks/'+str(interaction.guild.id) + '-settings.json', 'r').read())
  except:
    xpsettings = None
  if not xpsettings:
    xpsettings = {
      "enabled": False,
      "xppermessage": 1,
      "xplevelincrement": 120,
      "xppercallminute": 1,
      "firstlevelxp": 20,
      "cardbackground": None,
      "levelupchannel": None,
      "dolevelupmessage": True,
      "levelupmessagetype": "embed",
      "roleasrank": False
    }
  xpsettings['enabled'] = enabled
  json.dump(xpsettings, open('xpranks/'+str(interaction.guild.id) + '-settings.json', 'w'), indent = 4)
  status = "enabled" if enabled else "disabled"
  embed = discord.Embed(title = "XP/Leveling System", description = f"Your leveling system has been successfully {status}.", color = embed_color_success)
  await interaction.followup.send(embed = embed)

        
    



async def xpsystemrankcard(interaction, user: discord.User = None):
  """Get your current xp rank

  Parameters
  ----------
  user : discord.User
      The user to get the rank from"""
  if not user:
    user = interaction.user
  await interaction.response.defer()
  try:
    xpsettings = json.loads(open('xpranks/'+str(interaction.guild.id) + '-settings.json', 'r').read())
  except:
    xpsettings = None
  if not xpsettings or not xpsettings['enabled']:
    embed = discord.Embed(title = "XP/Leveling System", description = "The XP/Leveling System is disabled on this server.", color = embed_color_error)
    return await interaction.followup.send(embed= embed)
  try:
    serverxp = json.loads(open('xpranks/'+str(interaction.guild.id)+'-users.json', 'r').read())
  except:
    serverxp = {}
  if not str(user.id) in serverxp.keys():
    serverxp[str(user.id)] = {"currentxp": 0, "currentlevel": 1}
  member = interaction.guild.get_member(user.id)
  username = user.name
  currentxp = serverxp[str(user.id)]["currentxp"]
  lastxp = 0
  nextxp = xpsettings["firstlevelxp"] + (serverxp[str(user.id)]["currentlevel"] - 1) * xpsettings["xplevelincrement"]
  current_level = serverxp[str(user.id)]['currentlevel']
  if xpsettings["roleasrank"]:
    member = interaction.guild.get_member(user.id)
    current_rank = member.roles[0].name
  else:
    sorted_members = sorted(serverxp.items(), key=lambda x: (x[1]['currentlevel'], x[1]['currentxp']), reverse=True)
    current_rank = next((index + 1 for index, (member_id, member_data) in enumerate(sorted_members) if member_id == str(user.id)), None)
  background = xpsettings["cardbackground"]
    
  image = await canvacord.rankcard(user = member,
                                username = username,
                                currentxp = currentxp,
                                lastxp = lastxp,
                                nextxp = nextxp,
                                level = current_level,
                                rank = current_rank,
                                background = background, ranklevelsep = ':', xpsep = '-')
  file = discord.File(filename = "rankcard.png", fp = image)
  await interaction.followup.send(file = file)


async def xpsystemleaderboard(interaction):
  await interaction.response.defer()
  try:
    xpsettings = json.loads(open('xpranks/'+str(interaction.guild.id) + '-settings.json', 'r').read())
  except:
    xpsettings = None
  if not xpsettings or not xpsettings['enabled']:
    return await interaction.followup.send('The XP//Leveling System is disabled on this server.')
  try:
      serverxp = json.loads(open('xpranks/' + str(interaction.guild.id) + '-users.json', 'r').read())
  except:
      return await interaction.followup.send('No leaderboard found on this server')
  sorted_members = sorted(serverxp.items(), key=lambda x: (x[1]['currentlevel'], x[1]['currentxp']), reverse=True)
  top_25 = sorted_members[:25]
  embed = discord.Embed(title='XP/Leveling Leaderboard', color = embed_color)
  for rank, (member_id, member_data) in enumerate(top_25, start=1):
    member = interaction.guild.get_member(int(member_id))
    if member:
      embed.add_field(name = f"#{rank} {member.display_name}", value=f"Level: {member_data['currentlevel']} | XP: {member_data['currentxp']}", inline=False)
    if interaction.guild.icon:
      embed.set_thumbnail(url = interaction.guild.icon.url)
  await interaction.followup.send(embed= embed)

@client.event
async def on_member_join(member):
  announcements = json.loads(open('announcements.json', 'r').read())
  if not str(member.guild.id) in announcements:
    announcements[str(member.guild.id)] = []
  for announcement in announcements[str(member.guild.id)]:
    try:
      if announcement["action"]== "join":
        if announcement["type"] == "banner":
          for l in ["banner_avatarcolor", "banner_textcolor"]:
            try:
              Color(announcement[l])
            except:
              announcement[l] = 'white'
          try:
            background_color = Color(announcement['banner_background'])
            background = None
          except:
            background_color = 'black'
            background = announcement['banner_background']
          image = await canvacord.welcomecard(user = member,
                                              background = background,
                                              avatarcolor = announcement['banner_avatarcolor'],
                                              topcolor = announcement['banner_textcolor'],
                                              bottomcolor=announcement['banner_textcolor'],
                                              backgroundcolor=background_color,
                                              font=None,
                                              toptext=announcement['banner_toptext'],
                                              bottomtext=announcement['banner_bottomtext'])
          file = discord.File(filename = 'welcome.png', fp = image)
          for channel in member.guild.channels:
            if channel.id == announcement["channel"]:
              await channel.send(file = file)
        if announcement["type"] == "embed":
          try:
            join_embed_color = Color(n[0]['embed_color']).hex_l
          except:
            join_embed_color = Color('white').hex_l
          join_embed_color = int(join_embed_color.replace('#',''), 16)
          embed = discord.Embed(title = announcement["embed_title"].replace("{server}", member.guild.name).replace("{user_name}", member.name),
                                description = announcement["embed_description"].replace("{server}", member.guild.name).replace("{user_name}", member.name),
                                color = join_embed_color)
          for channel in member.guild.channels:
            if channel.id == announcement["channel"]:
              await channel.send(embed = embed)
        if announcement["type"] == "text":
          for channel in member.guild.channels:
            if channel.id == announcement["channel"]:
              await channel.send(announcement["text_message"].replace("{server}", member.guild.name).replace("{user_name}", member.name))
    except:
      pass




@client.event
async def on_member_remove(member):
  announcements = json.loads(open('announcements.json', 'r').read())
  if not str(member.guild.id) in announcements:
    announcements[str(member.guild.id)] = []
  for announcement in announcements[str(member.guild.id)]:
    try:
      if announcement["action"]== "leave":
        if announcement["type"] == "banner":
          for l in ["banner_avatarcolor", "banner_textcolor"]:
            try:
              Color(announcement[l])
            except:
              announcement[l] = 'white'
          try:
            background_color = Color(announcement['banner_background'])
            background = None
          except:
            background_color = 'black'
            background = announcement['banner_background']
          image = await canvacord.welcomecard(user = member,
                                              background = background,
                                              avatarcolor = announcement['banner_avatarcolor'],
                                              topcolor = announcement['banner_textcolor'],
                                              bottomcolor=announcement['banner_textcolor'],
                                              backgroundcolor=background_color,
                                              font=None,
                                              toptext=announcement['banner_toptext'],
                                              bottomtext=announcement['banner_bottomtext'])
          file = discord.File(filename = 'welcome.png', fp = image)
          for channel in member.guild.channels:
            if channel.id == announcement["channel"]:
              await channel.send(file = file)
        if announcement["type"] == "embed":
          try:
            join_embed_color = Color(n[0]['embed_color']).hex_l
          except:
            join_embed_color = Color('white').hex_l
          join_embed_color = int(join_embed_color.replace('#',''), 16)
          embed = discord.Embed(title = announcement["embed_title"].replace("{server}", member.guild.name).replace("{user_name}", member.name),
                                description = announcement["embed_description"].replace("{server}", member.guild.name).replace("{user_name}", member.name),
                                color = join_embed_color)
          for channel in member.guild.channels:
            if channel.id == announcement["channel"]:
              await channel.send(embed = embed)
        if announcement["type"] == "text":
          for channel in member.guild.channels:
            if channel.id == announcement["channel"]:
              await channel.send(announcement["text_message"].replace("{server}", member.guild.name).replace("{user_name}", member.name))
    except:
      pass




async def complete_announcement_label(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
  announcements = json.loads(open('announcements.json', 'r').read())
  n = [i for i in announcements[str(interaction.guild.id)] if current in i["label"]]
  guild_id = interaction.guild.id
  return [app_commands.Choice(name = s["label"], value = s["label"]) for s in n]

@app_commands.autocomplete(label = complete_announcement_label)
async def announcements_remove_join(interaction, label: str):
  """Remove an announcement

  Parameters
  ----------
  label : str
      The label of the announcement to remove"""
  await interaction.response.defer(ephemeral = True)
  staff = json.loads(open('staff.json', 'r').read())
  if not interaction.guild:
    embed = discord.Embed(title="Announcements", description="This command can only be used in a server!", color = embed_color_error)
    await interaction.followup.send(embed = embed)
    return
  isStaff = False
  member = interaction.guild.get_member(interaction.user.id)
  if str(interaction.guild.id) in staff:
    for role in member.roles:
      if role.id in staff[str(interaction.guild.id)]["manager"]:
        isStaff = True
  if member.guild_permissions.administrator or member.id == interaction.guild.owner.id:
    isStaff = True
  if not isStaff:
    embed = discord.Embed(title="Announcements", description="You don't have permission to use this command!", color = embed_color_error)
    await interaction.followup.send(embed = embed)
    return
  announcements = json.loads(open('announcements.json', 'r').read())
  if not str(member.guild.id) in announcements:
    announcements[str(member.guild.id)] = []
  for n in announcements[str(member.guild.id)]:
    if n["label"] == label:
      announcements[str(member.guild.id)].remove(n)
  json.dump(announcements, open('announcements.json', 'w'), indent = 4)
  embed = discord.Embed(title="Announcements", description="The announcement with the label "+label+" got deleted.", color = embed_color_success)
  await interaction.followup.send(embed=embed)


@app_commands.choices(announcement_type = [
  app_commands.Choice(name="Banner", value="banner"),
  app_commands.Choice(name="Embed", value="embed"),
  app_commands.Choice(name="Text", value="text")
])
@app_commands.choices(action = [
  app_commands.Choice(name="Join", value="join"),
  app_commands.Choice(name="Leave", value="leave")
])
async def announcements_add_join(interaction, label: str, channel: discord.TextChannel, announcement_type: str, action: str):
  """Add a new announcement

  Parameters
  ----------
  label : str
      Label this announcement
  channel : discord.TextChannel
      The channel to send the join announcement to
  announcement_type : str
      The type of the announcement to send
  action : str
      The event when this announcement shall be sent"""
  await interaction.response.defer(ephemeral = True)
  staff = json.loads(open('staff.json', 'r').read())
  if not interaction.guild:
    embed = discord.Embed(title="Announcements", description="This command can only be used in a server!", color = embed_color_error)
    await interaction.followup.send(embed = embed)
    return
  isStaff = False
  member = interaction.guild.get_member(interaction.user.id)
  if str(interaction.guild.id) in staff:
    for role in member.roles:
      if role.id in staff[str(interaction.guild.id)]["manager"]:
        isStaff = True
  if member.guild_permissions.administrator or member.id == interaction.guild.owner.id:
    isStaff = True
  if not isStaff:
    embed = discord.Embed(title="Announcements", description="You don't have permission to use this command!", color = embed_color_error)
    await interaction.followup.send(embed = embed)
    return
  announcements = json.loads(open('announcements.json', 'r').read())
  if not str(member.guild.id) in announcements:
    announcements[str(member.guild.id)] = []
  n = [i for i in announcements[str(member.guild.id)] if i["label"] == label]
  if len(n) !=0:
    embed = discord.Embed(title="Announcements", description="An announcement with this label already exists in this server!", color = embed_color_error)
    await interaction.followup.send(embed = embed)
    return
  if action == 'join':
    announcements[str(member.guild.id)].append({
      "type": announcement_type,
      "text_message": "Welcome {user_name}\nEnjoy your stay in {server}!",
      "embed_color": "purple",
      "embed_title": "Welcome {user_name}",
      "embed_description": "Enjoy your stay in {server}!",
      "banner_background": "black",
      "banner_avatarcolor": "white",
      "banner_textcolor": "white",
      "banner_toptext": "Welcome {user_name}",
      "banner_bottomtext": "Enjoy your stay in {server}!",
      "channel": channel.id,
      "label": label,
      "action": action
    })
  if action == 'leave':
    announcements[str(member.guild.id)].append({
      "type": announcement_type,
      "text_message": "{user_name} left {server} 👋",
      "embed_color": "purple",
      "embed_title": "{user_name} left",
      "embed_description": "{server} will miss you.",
      "banner_background": "black",
      "banner_avatarcolor": "white",
      "banner_textcolor": "white",
      "banner_toptext": "{user_name} left",
      "banner_bottomtext": "{server} will miss you.",
      "channel": channel.id,
      "label": label,
      "action": action
    })
    
  json.dump(announcements, open('announcements.json', 'w'), indent = 4)
  n = [i for i in announcements[str(member.guild.id)] if i["label"] == label]
  if announcement_type == 'banner':
    for l in ["banner_avatarcolor", "banner_textcolor"]:
      try:
        Color(n[0][l])
      except:
        n[0][l] = 'white'
    try:
      background_color = Color(n[0]['banner_background'])
      background = None
    except:
      background_color = 'black'
      background = n[0]['banner_background']
    image = await canvacord.welcomecard(user = member,
                                        background = background,
                                        avatarcolor = n[0]['banner_avatarcolor'],
                                        topcolor = n[0]['banner_textcolor'],
                                        bottomcolor=n[0]['banner_textcolor'],
                                        backgroundcolor=background_color,
                                        font=None,
                                        toptext=n[0]['banner_toptext'],
                                        bottomtext=n[0]['banner_bottomtext'])
    file = discord.File(filename='welcome.png', fp=image)
    class JoinAnnouncementBannerEditView(ui.View):
      def __init__(self, member, label):
        super().__init__(timeout = None)
        self.member = member
        self.label = label
      @ui.button(label = "Edit banner", style = discord.ButtonStyle.green)
      async def edit_banner(self, interaction, button):
        class EditColorsModal(ui.Modal, title='Edit banner'):
          announcements = json.loads(open('announcements.json', 'r').read())
          n = [i for i in announcements[str(member.guild.id)] if i["label"] == label][0]
          background = ui.TextInput(label = 'Background', default = n["banner_background"])
          avatarcolor = ui.TextInput(label = 'Avatar color', default = n["banner_avatarcolor"])
          textcolor = ui.TextInput(label = 'Text color', default = n["banner_textcolor"])
          toptext = ui.TextInput(label = 'Top line', default = n["banner_toptext"])
          bottomtext = ui.TextInput(label = 'Bottom line', default = n["banner_bottomtext"])
          def __init__(self, member, label):
            super().__init__(timeout = None)
            self.label = label
            self.member = member

          async def on_submit(self, interaction):
            await interaction.response.defer(ephemeral=True)
            announcements = json.loads(open('announcements.json', 'r').read())
            n = next((index for index, announcement in enumerate(announcements[str(member.guild.id)]) if announcement["label"] == label), None)
            announcements[str(member.guild.id)][n]['banner_background'] = self.background.value
            announcements[str(member.guild.id)][n]['banner_avatarcolor'] = self.avatarcolor.value
            announcements[str(member.guild.id)][n]['banner_textcolor'] = self.textcolor.value
            announcements[str(member.guild.id)][n]['banner_toptext'] = self.toptext.value
            announcements[str(member.guild.id)][n]['banner_bottomtext'] = self.bottomtext.value
            for l in ["banner_avatarcolor", "banner_textcolor"]:
              try:
                Color(announcements[str(member.guild.id)][n][l])
              except:
                announcements[str(member.guild.id)][n][l] = 'white'
            json.dump(announcements, open('announcements.json', 'w'), indent = 4)
            n = [i for i in announcements[str(member.guild.id)] if i["label"] == label]
            try:
              background_color = Color(n[0]['banner_background'])
              background = None
            except:
              background_color = 'black'
              background = n[0]['banner_background']
            image = await canvacord.welcomecard(user = self.member,
                                                background = background,
                                                avatarcolor = n[0]['banner_avatarcolor'],
                                                topcolor = n[0]['banner_textcolor'],
                                                bottomcolor=n[0]['banner_textcolor'],
                                                backgroundcolor=background_color,
                                                font=None,
                                                toptext=n[0]['banner_toptext'],
                                                bottomtext=n[0]['banner_bottomtext'])
            file = discord.File(filename='welcome.png', fp=image)
            await interaction.followup.send(content = "Saved banner: ", file = file, view = JoinAnnouncementBannerEditView(member = self.member, label = self.label), ephemeral = True)
            
          
        await interaction.response.send_modal(EditColorsModal(member = self.member, label = self.label))


    await interaction.followup.send(content = "Saved banner: ", file = file, view = JoinAnnouncementBannerEditView(member = member, label = label))
  elif announcement_type == 'embed':
    try:
      join_embed_color = Color(n[0]['embed_color']).hex_l
    except:
      join_embed_color = Color('white').hex_l
    join_embed_color = int(join_embed_color.replace('#',''), 16)
    embed = discord.Embed(title = n[0]["embed_title"].replace("{server}", interaction.guild.name).replace("{user_name}", member.name),
                          description = n[0]["embed_description"].replace("{server}", interaction.guild.name).replace("{user_name}", member.name),
                          color = join_embed_color)
    if member.avatar:
      embed.set_thumbnail(url = member.avatar.url)
    class JoinAnnouncementEmbedEditView(ui.View):
      def __init__(self, member, label):
        super().__init__(timeout = None)
        self.member = member
        self.label = label
      @ui.button(label = "Edit embed", style = discord.ButtonStyle.green)
      async def edit_banner(self, interaction, button):
        class EditColorsModal(ui.Modal, title='Edit embed'):
          announcements = json.loads(open('announcements.json', 'r').read())
          n = [i for i in announcements[str(member.guild.id)] if i["label"] == label][0]
          color = ui.TextInput(label = 'Color', default = n["embed_color"])
          etitle = ui.TextInput(label = 'Title', default = n["embed_title"])
          description = ui.TextInput(label = 'Description', default = n["embed_description"], style=discord.TextStyle.long)
          def __init__(self, member, label):
            super().__init__(timeout = None)
            self.label = label
            self.member = member

          async def on_submit(self, interaction):
            await interaction.response.defer(ephemeral=True)
            announcements = json.loads(open('announcements.json', 'r').read())
            n = next((index for index, announcement in enumerate(announcements[str(member.guild.id)]) if announcement["label"] == label), None)
            announcements[str(member.guild.id)][n]['embed_color'] = self.color.value
            announcements[str(member.guild.id)][n]['embed_title'] = self.etitle.value
            announcements[str(member.guild.id)][n]['embed_description'] = self.description.value
            try:
              join_embed_color = Color(announcements[str(member.guild.id)][n]['embed_color']).hex_l
              print(join_embed_color)
            except:
              join_embed_color = Color('white').hex_l
            join_embed_color = int(join_embed_color.replace('#',''), 16)
            json.dump(announcements, open('announcements.json', 'w'), indent = 4)
            n = [i for i in announcements[str(member.guild.id)] if i["label"] == label]
            embed = discord.Embed(title = n[0]["embed_title"].replace("{server}", interaction.guild.name).replace("{user_name}", member.name),
                                  description = n[0]["embed_description"].replace("{server}", interaction.guild.name).replace("{user_name}", member.name),
                                  color = join_embed_color)
            if member.avatar:
              embed.set_thumbnail(url = member.avatar.url)
            await interaction.followup.send(content = 'Saved embed: ', embed = embed, view = JoinAnnouncementEmbedEditView(member = self.member, label = self.label), ephemeral = True)
        await interaction.response.send_modal(EditColorsModal(member = self.member, label = self.label))
    await interaction.followup.send(content = 'Saved embed: ', embed = embed, view = JoinAnnouncementEmbedEditView(member = member, label = label))
  else:
    class JoinAnnouncementTextEditView(ui.View):
      def __init__(self, member, label):
        super().__init__(timeout = None)
        self.member = member
        self.label = label
      @ui.button(label = "Edit text", style = discord.ButtonStyle.green)
      async def edit_banner(self, interaction, button):
        class EditColorsModal(ui.Modal, title='Edit text'):
          announcements = json.loads(open('announcements.json', 'r').read())
          n = [i for i in announcements[str(member.guild.id)] if i["label"] == label][0]
          message = ui.TextInput(label = 'Message', default = n["text_message"], style=discord.TextStyle.long)
          def __init__(self, member, label):
            super().__init__(timeout = None)
            self.label = label
            self.member = member

          async def on_submit(self, interaction):
            await interaction.response.defer(ephemeral=True)
            announcements = json.loads(open('announcements.json', 'r').read())
            n = next((index for index, announcement in enumerate(announcements[str(member.guild.id)]) if announcement["label"] == label), None)
            announcements[str(member.guild.id)][n]['text_message'] = self.message.value
            json.dump(announcements, open('announcements.json', 'w'), indent = 4)
            n = [i for i in announcements[str(member.guild.id)] if i["label"] == label]
            await interaction.followup.send(content = "Saved text: \n\n"+n[0]['text_message'].replace("{server}", interaction.guild.name).replace("{user_name}", member.name), view = JoinAnnouncementTextEditView(member = self.member, label = self.label), ephemeral = True)
            
          
        await interaction.response.send_modal(EditColorsModal(member = self.member, label = self.label))
    await interaction.followup.send(content = 'Saved text: \n\n'+n[0]['text_message'].replace("{server}", interaction.guild.name).replace("{user_name}", member.name), view = JoinAnnouncementTextEditView(member = member, label = label))
    


if __name__ == '__main__':
  webserver_thread = threading.Thread(target=app.run, kwargs = {'port': 80, 'host': '0.0.0.0'})
  webserver_thread.start()
  client.run(TOKEN)