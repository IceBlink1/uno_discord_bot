import discord

from game import *
from discord.ext import commands
TOKEN = 'your token'
# 285615713280

bot = commands.Bot(case_insensitive=True, intents=discord.Intents.all(), command_prefix='/')


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

