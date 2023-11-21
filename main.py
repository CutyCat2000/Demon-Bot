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
      if role.id in staff["moderator"] or role.id in staff["manager"]:
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
        if role.id in staff["moderator"] or role.id in staff["manager"]:
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
        if role.id in staff["moderator"] or role.id in staff["manager"]:
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
                if guild.id == 1173641101542969444:
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
  if message.author.id == client.user.id:
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
    return await interaction.followup.send('The XP//Leveling System is disabled on this server.')
  try:
    serverxp = json.loads(open('xpranks/'+str(interaction.guild.id)+'-users.json', 'r').read())
  except:
    return await interaction.followup.send('Noone sent a message yet.')
  if not str(user.id) in serverxp.keys():
    return await interaction.followup.send('Please send a message first.')
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
      return await ctx.send('No one sent a message yet.')
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



if __name__ == '__main__':
  webserver_thread = threading.Thread(target=app.run, kwargs = {'port': 80, 'host': '0.0.0.0'})
  webserver_thread.start()
  client.run(TOKEN)