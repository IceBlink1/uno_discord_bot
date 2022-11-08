import discord
from discord.ext import commands
from discord.ui import View, Button

from game import *

f = open('./token.txt', 'r')
TOKEN = f.read()

channel_to_game: dict[int, tuple[Game, discord.Message]] = {}

bot = commands.Bot(case_insensitive=True, intents=discord.Intents.all(), command_prefix='/')


@bot.command(name='uno', description='Starts a new uno game')
@commands.guild_only()
async def uno(ctx: commands.Context):
    admin = Player(ctx.message.author.id, ctx.message.author.display_name)
    if ctx.channel.id in channel_to_game:
        game, _ = channel_to_game[ctx.channel.id]
        await ctx.send(
            content=f'There is already a game in progress hosted by {game.admin.nickname}', ephemeral=True)
        return
    g = Game(admin)
    msg = 'Initialized a new game'
    v = View()

    async def leave_button_callback(interaction: discord.Interaction):
        player = next((player for player in g.players if player.discord_tag == interaction.user.id), None)
        if player is None:
            await interaction.response.send_message(content='You are not part of the current game', ephemeral=True)
        try:
            g.remove_player(player)
        except RuntimeError:
            await interaction.response.send_message(content='You cannot leave if you are an admin', ephemeral=True)
        await reformat_game_message(ctx.channel.id)

    async def join_game_callback(interaction: discord.Interaction):
        player = Player(interaction.user.id, interaction.user.nick)
        try:
            g.add_player(player)
        except RuntimeError as re:
            await interaction.response.send_message(content='You cannot join a game twice', ephemeral=True)
        await reformat_game_message(ctx.channel.id)

    async def abort_button_callback(interaction: discord.Interaction):
        if admin.discord_tag != interaction.user.id:
            await interaction.response.send_message(content='Only an admin can abort the game', ephemeral=True)
        else:
            await interaction.response.send_message(content='The game is successfully aborted', ephemeral=True)
            await abort_game(interaction.message)

    join_button = Button(label='Join game')
    join_button.callback = join_game_callback
    leave_button = Button(label='Leave game')
    leave_button.callback = leave_button_callback
    abort_button = Button(label='Abort game')
    abort_button.callback = abort_button_callback
    v.add_item(leave_button)
    v.add_item(join_button)
    v.add_item(abort_button)
    game_message = await ctx.send(content=msg, view=v)
    channel_to_game[ctx.channel.id] = g, game_message
    g.on_finished_callbacks.append(lambda p: finish_game(game_message, p))


async def reformat_game_message(channel_id: int):
    game, game_message = channel_to_game[channel_id]
    # todo: handling game state

async def finish_game(message: discord.Message, winner: Player):
    await message.edit(content=f'The game is finished. The winner is {winner.nickname}')
    channel_to_game.pop(message.channel.id, None)


async def abort_game(message: discord.Message):
    await message.edit(content=f'The game is aborted.')
    channel_to_game.pop(message.channel.id, None)


# @bot.event
# async def on_guild_available(guild: discord.Guild):
#     print('on_guild_available is called')
#     _ = await bot.tree.sync(guild=guild)
#     print(_)


# bot.add_command(uno)
bot.run(token=TOKEN)

# if __name__ == '__main__':
#     a = Player("a", "a")
#     b = Player("b", "b")
#     c = Player('c', 'c')
#     g = Game(admin=a)
#     g.add_player(b)
#     g.add_player(c)
#     g.start_game()
#     print(g)
#     g.process_turn(a.discord_tag, None, None)
#     g.process_turn(c.discord_tag, None, None)
#     g.process_turn(b.discord_tag, None, None)
#     g.process_turn(a.discord_tag, None, None)
#     print(g)
