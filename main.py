import discord
from discord.ext import commands
from discord.ui import View, Button

from game import *

f = open('token.txt', 'r')
TOKEN = f.read()

channel_to_game: dict[int, tuple[Game, discord.Message]] = {}
game_to_player_cards: dict[Game, dict[Player, list[discord.Message]]] = {}

bot = commands.Bot(case_insensitive=True, intents=discord.Intents.all(), command_prefix='/')


async def finish_game(message: discord.Message, winner: Player):
    await message.edit(content=f'The game is finished. The winner is {winner.nickname}', view=View())
    (g, _) = channel_to_game.pop(message.channel.id, None)
    game_to_player_cards.pop(g)


async def abort_game(message: discord.Message):
    await message.edit(content=f'The game is aborted.', view=View())
    (g, _) = channel_to_game.pop(message.channel.id, None)
    game_to_player_cards.pop(g)


async def join_game_callback(interaction: discord.Interaction):
    g, _ = channel_to_game[interaction.channel.id]
    player = Player(interaction.user.id, interaction.user.display_name)
    try:
        await g.add_player(player)
        await interaction.response.defer()
    except RuntimeError as re:
        print(re)
        await interaction.response.send_message(content='You cannot join a game twice', ephemeral=True)


async def leave_button_callback(interaction: discord.Interaction):
    g, _ = channel_to_game[interaction.channel.id]
    player = next((player for player in g.players if player.discord_tag == interaction.user.id), None)
    if player is None:
        await interaction.response.send_message(content='You are not part of the current game', ephemeral=True)
    try:
        await g.remove_player(player)
        await interaction.response.defer()
    except RuntimeError:
        await interaction.response.send_message(content='You cannot leave if you are an admin', ephemeral=True)


async def abort_button_callback(interaction: discord.Interaction):
    g, _ = channel_to_game[interaction.channel.id]
    if g.admin.discord_tag != interaction.user.id:
        await interaction.response.send_message(content='Only an admin can abort the game', ephemeral=True)
    else:
        await interaction.response.send_message(content='The game is successfully aborted', ephemeral=True)
        await abort_game(interaction.message)


async def start_game_callback(interaction: discord.Interaction):
    g, _ = channel_to_game[interaction.channel.id]
    if interaction.user.id != g.admin.discord_tag:
        await interaction.response.send_message(content='Only an admin can start the game', ephemeral=True)
    try:
        game_to_player_cards[g] = {}
        for player in g.players:
            game_to_player_cards[g][player] = []
        await g.start_game()
        await interaction.response.defer()
    except RuntimeError:
        await interaction.response.send_message(content='Cannot start game right now', ephemeral=True)


def create_init_buttons(start_active: bool) -> list[Button]:
    join_button = Button(label='Join game')
    join_button.callback = join_game_callback
    leave_button = Button(label='Leave game')
    leave_button.callback = leave_button_callback
    abort_button = Button(label='Abort game')
    abort_button.callback = abort_button_callback
    start_button = Button(label='Start game', disabled=not start_active)
    start_button.callback = start_game_callback
    return [join_button, leave_button, abort_button, start_button]


def create_wild_pick_color_view(game: Game, player: Player, card_id: int) -> View:
    color_buttons = []
    for color in Color:
        async def color_button_callback(interaction: discord.Interaction):
            await game.process_turn(discord_tag=player.discord_tag, card_id=card_id,
                                    wild_color=Color(int(interaction.data['custom_id'])))

            await interaction.response.edit_message(content='Your hand', view=create_view_card_view(game, player))

        color_buttons.append(Button(custom_id=str(color.value), label=f'{color}'))
        color_buttons[-1].callback = color_button_callback

    async def return_color_button_callback(interaction: discord.Interaction):
        await game.process_turn(discord_tag=player.discord_tag, card_id=card_id,
                                wild_color=None)

        await interaction.response.edit_message(content='Your hand', view=create_view_card_view(game, player))

    color_buttons.append(Button(label='Back'))
    color_buttons[-1].callback = return_color_button_callback
    v = View()
    for i in color_buttons:
        v.add_item(i)
    return v


def create_view_card_view(game: Game, player: Player) -> View:
    async def draw_card_callback(interaction: discord.Interaction):
        await game.process_turn(player.discord_tag, None, None)
        await interaction.response.defer()
        pass

    buttons = []
    for card in game.playersToCards[player]:
        async def regular_card_callback(interaction: discord.Interaction):
            await game.process_turn(player.discord_tag, int(interaction.data['custom_id']), None)
            await interaction.response.defer()

        async def wild_card_callback(interaction: discord.Interaction):
            await interaction.response.edit_message(content='Your hand',
                                                    view=create_wild_pick_color_view(game, player, int(
                                                        interaction.data['custom_id'])))

        buttons.append(Button(label=f'{card}', custom_id=str(card.id), disabled=(
                not game.is_playable(card) or game.current_player.discord_tag != player.discord_tag)))
        if isinstance(card, Wild) or isinstance(card, WildPlus):
            buttons[-1].callback = wild_card_callback
        else:
            buttons[-1].callback = regular_card_callback
    buttons.append(Button(label='Draw a card', disabled=game.current_player.discord_tag != player.discord_tag))
    buttons[-1].callback = draw_card_callback
    v = View()
    for button in buttons:
        v.add_item(button)
    return v


async def view_cards_button_callback(interaction: discord.Interaction):
    (g, _) = channel_to_game[interaction.channel.id]
    p = next((player for player in g.players if player.discord_tag == interaction.user.id), None)
    if p is None:
        await interaction.response.send_message(content='You are not participating in this game.', ephemeral=True)
    await interaction.response.send_message(content='Your hand', view=create_view_card_view(g, p), ephemeral=True)
    msg = await interaction.original_response()
    game_to_player_cards[g][p].append(msg)


def create_in_game_buttons() -> list[Button]:
    view_cards_button = Button(label='View cards')
    view_cards_button.callback = view_cards_button_callback
    abort_button = Button(label='Abort game')
    abort_button.callback = abort_button_callback

    return [view_cards_button, abort_button]


async def reformat_game_message(channel_id: int):
    game, game_message = channel_to_game[channel_id]
    v = View()
    if game.state == GameState.INITIALIZED or game.state == GameState.READY_TO_START:
        for button in create_init_buttons(game.state == GameState.READY_TO_START):
            v.add_item(button)
        players_str = '\n'.join(list(map(lambda p: p.nickname, game.players)))
        msg = f'Initialized a new game\nCurrently in game:\n{players_str}'
        await game_message.edit(content=msg, view=v)
    if game.state == GameState.ONGOING:
        for button in create_in_game_buttons():
            v.add_item(button)
        players_str = '\n'.join(
            list(map(lambda p: f'{p.nickname} – {len(game.playersToCards[p])} cards', game.players)))

        msg = f'The game is ongoing\nIt is {game.current_player.nickname}\'s turn\nCurrent pickup stack is {game.pickup_stack}\nCurrent color is {game.current_color}\nLast card was {game.current_card}\n{players_str}\n'
        await game_message.edit(content=msg, view=v)
        for player in game.players:
            for message in game_to_player_cards[game][player]:
                await message.edit(content='Your hand', view=create_view_card_view(game, player))


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
    msg = f'Initialized a new game\nCurrently in game:\n{admin.nickname}'
    v = View()

    for button in create_init_buttons(False):
        v.add_item(button)
    game_message = await ctx.send(content=msg, view=v)
    channel_to_game[ctx.channel.id] = g, game_message
    g.on_ready_callbacks.append(lambda: reformat_game_message(ctx.channel.id))
    g.on_initialized_callbacks.append(lambda: reformat_game_message(ctx.channel.id))
    g.on_ongoing_callbacks.append(lambda: reformat_game_message(ctx.channel.id))
    g.on_finished_callbacks.append(lambda p: finish_game(game_message, p))
    g.on_player_count_changed_callbacks.append(lambda: reformat_game_message(ctx.channel.id))
    g.on_turn_completed_callbacks.append(lambda: reformat_game_message(ctx.channel.id))


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
