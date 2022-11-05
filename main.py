import discord

from game import *
from discord import Embed
from discord.ext import commands
from discord.ui import View, Button

TOKEN = 'your token'
# 285615713280

channel_to_game: dict[int, tuple[Game, discord.Message]] = {}

bot = commands.Bot(case_insensitive=True, intents=discord.Intents.all(), command_prefix='/')


@bot.command(name='uno')
async def uno(ctx: commands.Context):
    admin = Player(ctx.message.author.id, ctx.message.author.display_name)
    if ctx.channel.id in channel_to_game:
        game, _ = channel_to_game[ctx.channel.id]
        await ctx.send(
            content=f'There is already a game in progress hosted by ${game.admin.discord_tag}')
        return
    g = Game(admin)
    msg = 'Initialized a new game'

    _, _, game_message = await ctx.send(content=msg, view=View())
    channel_to_game[ctx.channel.id] = g, game_message
    g.on_finished_callbacks.append(lambda p: finish_game(game_message, p))


def reformat_game_message(channel_id: int):
    game, game_message = channel_to_game[channel_id]


def finish_game(message: discord.Message, winner: Player):
    message.edit(content=f'The game is finished. The winner is {winner.nickname}')
    channel_to_game.pop(message.channel.id, None)


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
