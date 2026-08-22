import os
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
from storage.balance import get_balance, update_balance
from game.game_manager import game_manager
from game.player import Player
from game.view import PokerBettingView
from poker.winner import determine_winner


load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

class PokerBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # 개발용/테스트용 슬래시 명령어 즉시 동기화
        await self.tree.sync()
        print("슬래시 명령어가 성공적으로 동기화되었습니다.")

bot = PokerBot()

@bot.event
async def on_ready():
    print(f"로그인 완료: {bot.user.name} ({bot.user.id})")

@bot.tree.command(name="ping", description="봇의 반응 속도를 확인합니다.")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"🏓 퐁! ({round(bot.latency * 1000)}ms)")

@bot.tree.command(name="잔고", description="자신의 포커 칩 잔고를 확인합니다.")
async def balance(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    chips = get_balance(user_id)
    await interaction.response.send_message(f"💰 **{interaction.user.display_name}**님의 잔고: **{chips}** 칩")

# ==========================================
# STEP 7 & 8 & 9: 포커 관리 및 플레이 명령어
# ==========================================

@bot.tree.command(name="포커생성", description="현재 채널에 새로운 텍사스 홀덤 게임을 생성합니다.")
async def create_poker(interaction: discord.Interaction):
    channel_id = interaction.channel_id
    host_id = str(interaction.user.id)
    
    if game_manager.get_game(channel_id) is not None:
        await interaction.response.send_message("❌ 이 채널에는 이미 대기 중이거나 진행 중인 포커 게임이 있습니다.", ephemeral=True)
        return

    game = game_manager.create_game(channel_id, host_id)
    
    chips = get_balance(host_id)
    if chips <= 0:
        await interaction.response.send_message("❌ 잔고가 부족하여 게임을 생성할 수 없습니다. (최소 1칩 필요)", ephemeral=True)
        game_manager.remove_game(channel_id)
        return

    host_player = Player(user_id=host_id, username=interaction.user.display_name, chips=chips)
    game.players[host_id] = host_player

    embed = discord.Embed(
        title="🃏 텍사스 홀덤 포커 게임 생성됨!",
        description=f"방장 **{interaction.user.display_name}**님이 게임을 개설했습니다.\n참가를 원하시는 분은 `/참가` 명령어를 입력해 주세요.",
        color=0x2ecc71
    )
    embed.add_field(name="현재 참가자 (1/9)", value=f"• {interaction.user.display_name} (💰{chips})", inline=False)
    embed.set_footer(text="최소 2명 이상 모이면 방장이 `/게임시작`을 할 수 있습니다.")
    
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="참가", description="현재 대기 중인 포커 게임에 참가합니다.")
async def join_poker(interaction: discord.Interaction):
    channel_id = interaction.channel_id
    user_id = str(interaction.user.id)
    
    game = game_manager.get_game(channel_id)
    
    if game is None:
        await interaction.response.send_message("❌ 현재 이 채널에 대기 중인 포커 게임이 없습니다. 먼저 `/포커생성`을 해주세요.", ephemeral=True)
        return
        
    if game.phase != "WAITING":
        await interaction.response.send_message("❌ 게임이 이미 시작되어 참가할 수 없습니다.", ephemeral=True)
        return

    if user_id in game.players:
        await interaction.response.send_message("⚠️ 이미 이 게임에 참가 신청 상태입니다.", ephemeral=True)
        return

    if len(game.players) >= 9:
        await interaction.response.send_message("❌ 이 게임방이 가득 찼습니다. (최대 9명)", ephemeral=True)
        return

    chips = get_balance(user_id)
    if chips <= 0:
        await interaction.response.send_message("❌ 칩이 부족하여 게임에 참가할 수 없습니다.", ephemeral=True)
        return

    new_player = Player(user_id=user_id, username=interaction.user.display_name, chips=chips)
    game.players[user_id] = new_player

    player_list_str = "\n".join([f"• {p.username} (💰{p.chips})" for p in game.players.values()])

    embed = discord.Embed(
        title="➕ 포커 참가자 추가",
        description=f"**{interaction.user.display_name}**님이 게임에 성공적으로 참가했습니다!",
        color=0x3498db
    )
    embed.add_field(name=f"현재 참가자 ({len(game.players)}/9)", value=player_list_str, inline=False)
    
    await interaction.response.send_message(embed=embed)


# main.py의 /게임시작 명령어를 아래 완성본 구조로 교체합니다.

@bot.tree.command(name="게임시작", description="대기 중인 포커 게임을 마감하고 곧바로 개인 카드를 배분합니다.")
async def begin_poker(interaction: discord.Interaction):
    channel_id = interaction.channel_id
    user_id = str(interaction.user.id)
    
    game = game_manager.get_game(channel_id)
    
    if game is None:
        await interaction.response.send_message("❌ 현재 이 채널에 대기 중인 포커 게임이 없습니다.", ephemeral=True)
        return

    if game.host_id != user_id:
        await interaction.response.send_message("❌ 방장만 게임을 시작할 수 있어요!", ephemeral=True)
        return

    if game.phase != "WAITING":
        await interaction.response.send_message("❌ 이미 시작된 게임입니다.", ephemeral=True)
        return

    if len(game.players) < 2:
        await interaction.response.send_message("⚠️ 최소 2명 이상의 플레이어가 참가해야 해요.", ephemeral=True)
        return

    # 지연 응답 활성화 (DM 전송 연산 보장)
    await interaction.response.defer(ephemeral=False)

    # 1. 즉시 프리플롭 상태 설정 및 블라인드 자동 정산
    game.phase = "PREFLOP"
    sb_id, bb_id = game.initialize_round()
    
    sb_player = game.players[sb_id]
    bb_player = game.players[bb_id]
    btn_player = game.players[game.player_order[game.btn_index]]

    # 2. 플레이어들에게 개인 카드 2장씩 자동 전송
    dm_failed_players = []
    for p_id, player in game.players.items():
        player.hole_cards = game.deck.draw(2)
        
        try:
            discord_user = await bot.fetch_user(int(p_id))
            card_str = " | ".join([str(card) for card in player.hole_cards])
            
            dm_embed = discord.Embed(
                title="🃏 나의 개인 카드",
                description=f"다른 사람에게 들키지 않게 조심하세요!\n\n**내 카드:**  ` {card_str} `",
                color=0xe74c3c
            )
            dm_embed.set_footer(text=f"채널: #{interaction.channel.name} | 텍사스 홀덤")
            await discord_user.send(embed=dm_embed)
        except discord.Forbidden:
            dm_failed_players.append(player.username)

    # 3. 칩 저장소 연동 데이터 반영
    update_balance(sb_id, -sb_player.current_bet)
    update_balance(bb_id, -bb_player.current_bet)

    # 4. 화려한 시작 브리핑 임베드 출력
    player_names = ", ".join([f"**{p.username}**" for p in game.players.values()])
    embed = discord.Embed(
        title="🚀 Texas Hold'em 경기 시작!!",
        description=f"참여자 명단: {player_names}\n모든 참가자의 DM으로 개인 카드가 비밀리에 배송되었습니다. 🤫",
        color=0xe74c3c
    )
    embed.add_field(name="📌 경기 포지션 기본선", value=f"🔘 **BTN**: {btn_player.username}\n🔹 **SB**: {sb_player.username} (💰{sb_player.current_bet}칩 강제 징수)\n🔸 **BB**: {bb_player.username} (💰{bb_player.current_bet}칩 강제 징수)", inline=False)
    
    if dm_failed_players:
        failed_list = ", ".join(dm_failed_players)
        embed.add_field(name="⚠️ DM 차단 알림", value=f"[{failed_list}]님은 개인 메시지 허용을 켜주셔야 카드가 보입니다.", inline=False)

    await interaction.followup.send(embed=embed)
    
    # 5. 자동화된 첫 번째 프리플롭 베팅 보드판 및 버튼 세트 즉시 출력!
    view = PokerBettingView(game, bot, update_game_board_message)
    await update_game_board_message(interaction.channel, view)


@bot.tree.command(name="딜링", description="포션을 배정하고 플레이어들에게 홀 카드를 배분합니다. (방장 전용)")
async def deal_cards(interaction: discord.Interaction):
    channel_id = interaction.channel_id
    user_id = str(interaction.user.id)
    
    game = game_manager.get_game(channel_id)
    
    if game is None:
        await interaction.response.send_message("❌ 현재 이 채널에 진행 중인 포커 게임이 없습니다.", ephemeral=True)
        return
        
    if game.host_id != user_id:
        await interaction.response.send_message("❌ 방장만 카드를 돌릴 수 있습니다.", ephemeral=True)
        return
        
    if game.phase != "PREFLOP":
        await interaction.response.send_message("❌ 이미 카드가 배분되었거나 올바른 단계가 아닙니다.", ephemeral=True)
        return

    # 대기 알림 (에페머럴로 처리하여 채널을 깔끔하게 유지)
    await interaction.response.send_message("🃏 카드를 섞고 플레이어들에게 배분하는 중입니다...", ephemeral=True)

    # 1. 게임 비즈니스 로직 초기화 실행 및 포지션 획득
    sb_id, bb_id = game.initialize_round()
    
    sb_player = game.players[sb_id]
    bb_player = game.players[bb_id]
    btn_player = game.players[game.player_order[game.btn_index]]

    # 2. 플레이어들에게 홀 카드 2장씩 드로우 및 DM 전송
    dm_failed_players = []
    for p_id, player in game.players.items():
        player.hole_cards = game.deck.draw(2)
        
        try:
            discord_user = await bot.fetch_user(int(p_id))
            card_str = " | ".join([str(card) for card in player.hole_cards])
            
            dm_embed = discord.Embed(
                title="🃏 나의 홀 카드 (Hole Cards)",
                description=f"이 카드는 타인에게 공개되지 않도록 주의하세요!\n\n**내 카드:**  ` {card_str} `",
                color=0xe74c3c
            )
            dm_embed.set_footer(text=f"채널: #{interaction.channel.name} | 텍사스 홀덤")
            await discord_user.send(embed=dm_embed)
        except discord.Forbidden:
            dm_failed_players.append(player.username)

    # 3. 가상 화폐 데이터베이스 반영
    update_balance(sb_id, -sb_player.current_bet)
    update_balance(bb_id, -bb_player.current_bet)

    # 4. 베팅 뷰 컴포넌트 생성 및 통합형 실시간 보드판 최초 출력
    view = PokerBettingView(game, bot, update_game_board_message)
    
    current_player = game.get_current_player()
    embed = discord.Embed(
        title="🎰 Texas Hold'em — 프리플롭 베팅 시작",
        description=f"모든 플레이어의 DM으로 홀 카드가 전송되었습니다.\n\n▶️ 현재 턴: ✨ **{current_player.username}** 차례입니다. 하단 버튼을 누르세요.",
        color=0xf1c40f
    )
    
    # 상단에 포지션 브리핑 요약 정보 추가
    embed.add_field(name="📌 라운드 포지션", value=f"🔘 **BTN**: {btn_player.username}\n🔹 **SB**: {sb_player.username} (💰{game.sb_amount}칩 강제 베팅)\n🔸 **BB**: {bb_player.username} (💰{game.bb_amount}칩 강제 베팅)", inline=False)
    
    player_status_list = []
    for p in game.players.values():
        state = "[FOLD]" if p.has_folded else "[ALL-IN]" if p.is_all_in else f"베팅: {p.current_bet}칩"
        player_status_list.append(f"• **{p.username}**: {state} (보유: 💰{p.chips})")
        
    embed.add_field(name="👥 플레이어 상태 현황", value="\n".join(player_status_list), inline=False)
    embed.add_field(name="💰 현재 메인 팟", value=f"**{game.pot}** 칩", inline=True)
    embed.add_field(name="📊 받아쳐야 할 최소 베팅금", value=f"**{game.current_bet}** 칩", inline=True)
    
    if dm_failed_players:
        failed_list = ", ".join(dm_failed_players)
        embed.add_field(name="⚠️ DM 전송 실패 경고", value=f"[{failed_list}]님은 개인 메시지 허용 설정을 확인해 주세요.", inline=False)

    # [중요] view=view를 명시하여 임베드 메시지 바로 밑에 디스코드 버튼들이 나타나도록 확정 전송합니다.
    await interaction.channel.send(embed=embed, view=view)


@bot.tree.command(name="플롭", description="공유 카드 3장을 오픈하고 플롭 베팅 라운드를 시작합니다. (방장 전용)")
async def deal_flop_cards(interaction: discord.Interaction):
    channel_id = interaction.channel_id
    user_id = str(interaction.user.id)
    
    game = game_manager.get_game(channel_id)
    
    # 1. 예외 및 유효성 검증
    if game is None:
        await interaction.response.send_message("❌ 현재 이 채널에 진행 중인 포커 게임이 없습니다.", ephemeral=True)
        return
        
    if game.host_id != user_id:
        await interaction.response.send_message("❌ 방장만 플롭 카드를 오픈할 수 있습니다.", ephemeral=True)
        return
        
    if game.phase != "FLOP":
        await interaction.response.send_message("❌ 아직 플롭 단계가 아닙니다. 프리플롭 베팅 라운드가 완전히 종료되어야 합니다.", ephemeral=True)
        return

    # 2. 비즈니스 로직 실행 (커뮤니티 카드 3장 오픈 및 턴 리셋)
    game.deal_flop()
    
    # 3. 새로운 베팅 뷰 컴포넌트 생성 및 플롭 안내 메시지 전송
    view = PokerBettingView(game, bot, update_game_board_message)
    
    await interaction.response.send_message("🌱 딜러가 바닥에 플롭 카드 3장을 깔고 있습니다...")
    await update_game_board_message(interaction.channel, view)


# ==========================================
#기존 공통 UI 보드판 렌더링 헬퍼 함수를 아래처럼 '공유 카드 표시 기능'을 포함해 교체/수정합니다.
# ==========================================
async def update_game_board_message(channel, view_instance):
    game = view_instance.game
    current_player = game.get_current_player()
    
    # 현재 라운드 한글 이름 매핑
    phase_names = {
        "PREFLOP": "프리플롭 (Pre-flop)",
        "FLOP": "플롭 (Flop)",
        "TURN": "턴 (Turn)",
        "RIVER": "리버 (River)"
    }
    current_phase_name = phase_names.get(game.phase, game.phase)
    
    embed = discord.Embed(
        title=f"🎰 Texas Hold'em — {current_phase_name} 베팅 진행 중",
        description=f"현재 턴: ✨ **{current_player.username}** 차례입니다. 버튼을 눌러주세요.",
        color=0xf1c40f
    )
    
    # 바닥에 깔린 공유 카드가 있다면 임베드에 보기 좋게 노출
    if game.community_cards:
        cards_str = "   ".join([f"` {str(card)} `" for card in game.community_cards])
        embed.add_field(name="🃏 커뮤니티 카드 (Community Cards)", value=cards_str, inline=False)
    else:
        embed.add_field(name="🃏 커뮤니티 카드 (Community Cards)", value="` 아직 오픈된 카드가 없습니다 `", inline=False)
    
    player_status_list = []
    for p in game.players.values():
        state = "[FOLD]" if p.has_folded else "[ALL-IN]" if p.is_all_in else f"베팅: {p.current_bet}칩"
        player_status_list.append(f"• **{p.username}**: {state} (보유: 💰{p.chips})")
        
    embed.add_field(name="👥 플레이어 상태 현황", value="\n".join(player_status_list), inline=False)
    embed.add_field(name="💰 현재 메인 팟", value=f"**{game.pot}** 칩", inline=True)
    embed.add_field(name="📊 받아쳐야 할 최소 베팅금", value=f"**{game.current_bet}** 칩", inline=True)
    
    await channel.send(embed=embed, view=view_instance)

async def process_showdown(channel, game):
    """생존자들의 패를 열어 족보를 비교하고 승자에게 상금 칩을 지급합니다."""
    # 1. 기권하지 않은(살아있는) 플레이어만 필터링
    active_players = {p_id: p for p_id, p in game.players.items() if not p.has_folded}
    
    # 예외 처리: 만약 베팅 도중 모두 기권하고 단 1명만 남았다면 그 사람이 즉시 승리
    if len(active_players) == 1:
        winner_id = list(active_players.keys())[0]
        winner = active_players[winner_id]
        
        # 상금 지급 및 가상화폐 DB 반영
        update_balance(winner_id, game.pot)
        
        embed = discord.Embed(
            title=f"🏆 기권승! {winner.username} 우승! 🎉",
            description=f"**{winner.username}**님이 최종 상금 **{game.pot}** 칩을 획득합니다. 💰",
            color=0x2ecc71
        )
        game_manager.remove_game(game.channel_id) # 게임 세션 종료 및 리셋
        await channel.send(embed=embed)
        return

    # 2. 족보 판단 모듈용 데이터 가공 ({player_id: [카드리스트]})
    # 주의: Player는 dataclass라 해시 불가능하므로 dict key로 쓸 수 없음 (unhashable type 에러 원인).
    # 대신 hashable한 player_id(user_id)를 key로 쓰고, 나중에 필요할 때 active_players로 다시 매핑한다.
    players_cards = {p_id: p.hole_cards for p_id, p in active_players.items()}
    
    # 3. 이전에 구현해둔 determine_winner 엔진 호출하여 승자와 승리 족보 획득
    # 반환 형식: (winner_ids_list, best_hand_info)
    winner_ids, hand_info = determine_winner(players_cards, game.community_cards)
    
    # winner_ids(플레이어 식별자 목록)를 실제 Player 객체 목록으로 변환
    winners = [active_players[w_id] for w_id in winner_ids]

    # 4. 동점자 처리를 위한 상금 쪼개기(Split Pot) 계산
    split_pot = game.pot // len(winners)
    
    embed = discord.Embed(
        title="최종 패 오픈 🃏",
        color=0xe74c3c
    )
    
    # 생존자들의 카드와 최종 족보 이름 매핑 브리핑
    # 4단계 evaluator.py의 evaluate_hand를 재활용하여 개별 족보 표기
    from poker.evaluator import evaluate_hand
    for p in active_players.values():
        score, kickers, rank_name = evaluate_hand(p.hole_cards + game.community_cards)
        p_cards_str = " | ".join([str(c) for c in p.hole_cards])
        embed.add_field(
            name=f"👤 {p.username}님의 카드", 
            value=f"` {p_cards_str} ` ➡️ **{rank_name}**", 
            inline=False
        )
        
    # 바닥에 깔린 5장의 공유 카드를 다시 한 번 리마인드
    com_cards_str = "   ".join([f"` {str(c)} `" for c in game.community_cards])
    embed.add_field(name="🃏 테이블의 최종 공유 카드", value=com_cards_str, inline=False)

    # 5. 승자 정산 및 축하 멘트 구성
    winner_names = []
    for winner in winners:
        winner_names.append(f"**{winner.username}**")
        update_balance(winner.user_id, split_pot) # 데이터베이스 칩 지급 반영

    # 우승 족보 한글 매핑 힌트 (예: 플러시, 트리플 등)
    best_rank_name = hand_info[2]

    embed.add_field(
        name="🏆 우승자 💰",
        value=f"우승자: {', '.join(winner_names)}\n우승 족보: ✨ **{best_rank_name}** ✨\n획득 상금: 각 **{split_pot}** 칩",
        inline=False
    )
    embed.set_footer(text="게임이 성공적으로 종료되었습니다. 새로운 경기를 시작하려면 다시 `/포커생성`을 해주세요!")
    
    # 6. 현재 채널의 포커 게임 메모리 삭제 (다음 판 개설을 위해 초기화)
    game_manager.remove_game(game.channel_id)
    
    await channel.send(embed=embed)

@bot.tree.command(name="게임종료", description="현재 채널에서 진행 중인 포커 게임을 강제로 종료합니다. (방장 전용)")
async def terminate_poker(interaction: discord.Interaction):
    channel_id = interaction.channel_id
    user_id = str(interaction.user.id)
    
    game = game_manager.get_game(channel_id)
    
    if game is None:
        await interaction.response.send_message("❌ 현재 이 채널에 대기 중이거나 진행 중인 포커 게임이 없습니다.", ephemeral=True)
        return
        
    if game.host_id != user_id and not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ 게임을 종료할 권한이 없습니다. 방장 또는 서버 관리자만 가능합니다.", ephemeral=True)
        return

    game_manager.remove_game(channel_id)

    embed = discord.Embed(
        title="🛑 포커 게임 강제 종료",
        description=f"**{interaction.user.display_name}**님에 의해 현재 채널의 포커 게임이 강제 종료되었습니다.",
        color=0xe74c3c
    )
    embed.set_footer(text="이제 이 채널에서 누구나 새로운 `/포커생성`을 할 수 있습니다.")
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="방삭제", description="오류 상태에 빠진 채널의 포커 방 데이터를 무조건 삭제합니다. (관리자 전용)")
async def delete_poker_room(interaction: discord.Interaction):
    channel_id = interaction.channel_id
    
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ 이 명령어는 서버 관리자(Administrator) 권한이 있는 유저만 사용할 수 있습니다.", ephemeral=True)
        return

    game = game_manager.get_game(channel_id)
    if game is None:
        await interaction.response.send_message("ℹ️ 현재 채널에 등록된 포커 방 데이터가 메모리에 존재하지 않습니다.", ephemeral=True)
        return

    game_manager.remove_game(channel_id)
    await interaction.response.send_message(f"🧹 **[초기화 완료]** 채널(`{channel_id}`)의 모든 포커 게임 세션 데이터가 강제 삭제되었습니다.")


# ==========================================
# 공통 UI 보드판 렌더링 헬퍼 함수
# ==========================================
async def update_game_board_message(channel, view_instance):
    game = view_instance.game
    current_player = game.get_current_player()
    
    embed = discord.Embed(
        title="🎰 Texas Hold'em — 프리플롭 베팅 진행 중",
        description=f"현재 턴: ✨ **{current_player.username}** 차례입니다. 버튼을 눌러주세요.",
        color=0xf1c40f
    )
    
    player_status_list = []
    for p in game.players.values():
        state = "[FOLD]" if p.has_folded else "[ALL-IN]" if p.is_all_in else f"베팅: {p.current_bet}칩"
        player_status_list.append(f"• **{p.username}**: {state} (보유: 💰{p.chips})")
        
    embed.add_field(name="👥 플레이어 상태 현황", value="\n".join(player_status_list), inline=False)
    embed.add_field(name="💰 현재 메인 팟", value=f"**{game.pot}** 칩", inline=True)
    embed.add_field(name="📊 받아쳐야 할 최소 베팅금", value=f"**{game.current_bet}** 칩", inline=True)
    
    # 턴이 바뀔 때마다 신규 메시지로 컴포넌트 버튼들과 함께 뿌려집니다.
    await channel.send(embed=embed, view=view_instance)


# main.py 파일에 아래의 도움말 명령어 추가 및 헬퍼 함수를 업데이트합니다.

@bot.tree.command(name="도움말", description="포커를 모르는 분들을 위한 규칙과 봇 명령어 가이드예요.")
async def poker_help(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🔰 텍사스 홀덤 포커 가이드",
        description="쉽게 포커를 익혀봅시다",
        color=0x3498db
    )
    embed.add_field(
        name="📌 텍사스 홀덤이 뭔가요?",
        value="1. 나만 볼 수 있는 **'개인 카드 2장'**을 받아요.\n"
              "2. 바닥에 모두가 공유하는 **'공유 카드 5장'**이 차례대로 깔려요.\n"
              "3. 총 7장 중 **가장 궁합이 좋은 5장 조합**을 만들어서 상대방과 겨루는 게임이에요.\n",
        inline=False
    )
    embed.add_field(
        name="🎮 베팅 버튼은 어떻게 누르나요?",
        value="• **체크 (그냥 넘기기):** 내기 돈을 더 올리지 않고 다음 사람에게 순서를 토스해요.\n"
              "• **콜 (금액 맞추기):** 앞 사람이 올린 베팅 금액과 똑같이 칩을 내고 게임에 계속 참가해요.\n"
              "• **레이즈 (판돈 키우기):** 판돈을 더 크게 키우고 싶을 때 버튼을 누르고 원하는 칩 개수를 입력해요.\n"
              "• **폴드 (다이·기권):** 이번 판 카드가 너무 안 좋으면 기권해서 손해를 최소화해요.",
        inline=False
    )
    embed.add_field(
        name="🛠️ 핵심 명령어 순서",
        value="`/포커생성` ➡️ 개설하기\n"
              "`/참가` ➡️ 친구들 참가하기 (최대 9명)\n"
              "`/게임시작` ➡️ 로비 닫고 게임 준비\n"
              "`/딜링` ➡️ 강제 판돈 징수 및 개인 카드 2장 DM 발송\n"
              "`/플롭` ➡️ 바닥에 공유 카드 3장 오픈하기",
        inline=False
    )
    await interaction.response.send_message(embed=embed)

# main.py 파일 내부에 아래 명령어를 새롭게 추가해 주세요.

@bot.tree.command(name="족보", description="텍사스 홀덤의 포커 족보 순위를 가장 높은 순서대로 보여줍니다.")
async def poker_hands(interaction: discord.Interaction):
    embed = discord.Embed(
        title="👑 텍사스 홀덤 족보 순위 가이드",
        description="내 카드와 바닥의 공유 카드를 조합하여 가장 높은 족보를 완성한 사람이 승리합니다.",
        color=0xea4335
    )
    
    embed.add_field(
        name="🥇 1위. 로얄 스트레이트 플러시 (Royal Flush)",
        value="동일한 문양(♠,◆,♥,♣)으로 **10, J, Q, K, A**가 모인 패 (나오면 무조건 승리)",
        inline=False
    )
    embed.add_field(
        name="🥈 2위. 스트레이트 플러시 (Straight Flush)",
        value="동일한 문양으로 숫자가 5장 연속되는 패 (예: ♠5, ♠6, ♠7, ♠8, ♠9)",
        inline=False
    )
    embed.add_field(
        name="🥉 3위. 포카드 (Four of a Kind)",
        value="문양에 상관없이 똑같은 숫자 4장이 모인 패 (예: 7이 4장)",
        inline=False
    )
    embed.add_field(
        name="✨ 4위. 풀하우스 (Full House)",
        value="똑같은 숫자 3장(트리플)과 똑같은 숫자 2장(원페어)이 결합된 패 (예: K 세 장 + 5 두 장)",
        inline=False
    )
    embed.add_field(
        name="🎨 5위. 플러시 (Flush)",
        value="숫자와 관계없이 **같은 문양 5장**이 모인 패 (예: ◆문양만 5장)",
        inline=False
    )
    embed.add_field(
        name="🏃‍♂️ 6위. 스트레이트 (Straight)",
        value="문양과 관계없이 **숫자가 5장 연속**으로 이어진 패 (예: 3, 4, 5, 6, 7)",
        inline=False
    )
    embed.add_field(
        name="☘️ 7위. 트리플 (Three of a Kind)",
        value="문양에 상관없이 똑같은 숫자 3장이 모인 패 (예: J가 3장)",
        inline=False
    )
    embed.add_field(
        name="👬 8위. 투페어 (Two Pair)",
        value="똑같은 숫자 쌍이 2개 만들어진 패 (예: 9 두 장 + Q 두 장)",
        inline=False
    )
    embed.add_field(
        name="🤝 9위. 원페어 (One Pair)",
        value="똑같은 숫자 쌍이 딱 1개 만들어진 패 (예: A 두 장)",
        inline=False
    )
    embed.add_field(
        name="🃏 10위. 하이카드 (High Card)",
        value="아무 족보도 완성되지 않았을 때, 내가 가진 카드 중 **가장 높은 숫자**",
        inline=False
    )
    embed.add_field(
            name="카드 순위",
            value="A > K > Q > J > 10 > 9 > 8 > 7 > 6 > 5 > 4 > 3 > 2\n\n",
            inline=False
        )
    
    embed.set_footer(text="💡 팁: 내 개인 카드 2장과 바닥의 공유 카드 5장, 총 7장 중 베스트 5장만 자동 계산됩니다.")
    await interaction.response.send_message(embed=embed)


# ==========================================
# 공통 UI 보드판 렌더링 헬퍼 함수 (친화적 멘트 리모델링)
# ==========================================
async def update_game_board_message(channel, view_instance):
    game = view_instance.game
    current_player = game.get_current_player()
    
    phase_names = {
        "PREFLOP": "첫 번째 베팅 (프리플롭)",
        "FLOP": "공유 카드 3장 오픈 단계 (플롭)",
        "TURN": "공유 카드 4장 오픈 단계 (턴)",
        "RIVER": "최종 카드 오픈 단계 (리버)"
    }
    current_phase_name = phase_names.get(game.phase, game.phase)
    
    embed = discord.Embed(
        title=f"🎰 Texas Hold'em — {current_phase_name}",
        description=f"▶️ 지금은 ✨ **{current_player.username}**님의 베팅 차례예요!\n하단 버튼을 눌러 액션을 정해 주세요.",
        color=0xf1c40f
    )
    
    if game.community_cards:
        cards_str = "   ".join([f"` {str(card)} `" for card in game.community_cards])
        embed.add_field(name="🃏 바닥에 깔린 공유 카드", value=cards_str, inline=False)
    else:
        embed.add_field(name="🃏 바닥에 깔린 공유 카드", value="` 아직 바닥에 공개된 카드가 없어요 `", inline=False)
    
    player_status_list = []
    for p in game.players.values():
        state = "🏳️ 기권함 (FOLD)" if p.has_folded else "💥 올인!! (ALL-IN)" if p.is_all_in else f"베팅함: {p.current_bet}칩"
        player_status_list.append(f"• **{p.username}**: {state} [보유 칩: 💰{p.chips}]")
        
    embed.add_field(name="👥 우리 테이블 참여자 상태", value="\n".join(player_status_list), inline=False)
    embed.add_field(name="💰 이번 판 누적 상금 팟", value=f"**{game.pot}** 칩", inline=True)
    embed.add_field(name="📊 참가용 최소 베팅금 기준선", value=f"**{game.current_bet}** 칩", inline=True)
    
    await channel.send(embed=embed, view=view_instance)

# main.py 파일 내부에 아래 명령어 2개를 새롭게 추가해 주세요.

@bot.tree.command(name="돈", description="특정 유저에게 칩을 지급하거나 차감합니다. (관리자 전용)")
@app_commands.describe(유저="칩을 관리할 유저를 선택해 주세요", 금액="지급할 금액")
async def manage_money(interaction: discord.Interaction, 유저: discord.Member, 금액: int):
    # 1. 관리자 권한 확인
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ 이 명령어는 서버 관리자(Administrator) 권한이 있는 분만 사용할 수 있어요!", ephemeral=True)
        return

    target_id = str(유저.id)
    
    # 2. 칩 데이터베이스 업데이트
    update_balance(target_id, 금액)
    new_balance = get_balance(target_id)

    if 금액 >= 0:
        await interaction.response.send_message(f"💰 **{유저.display_name}**님에게 **{금액}** 칩을 지급했습니다! (현재 잔고: **{new_balance}** 칩)")
    else:
        await interaction.response.send_message(f"📉 **{유저.display_name}**님의 잔고에서 **{abs(금액)}** 칩을 회수했습니다. (현재 잔고: **{new_balance}** 칩)")


@bot.tree.command(name="돈초기화", description="특정 유저의 칩 잔고를 처음 시작 금액인 1000칩으로 리셋합니다. (관리자 전용)")
@app_commands.describe(유저="칩을 초기화할 유저를 선택해 주세요")
async def reset_money(interaction: discord.Interaction, 유저: discord.Member):
    # 1. 관리자 권한 확인
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ 이 명령어는 서버 관리자(Administrator) 권한이 있는 사람만 사용할 수 있습니다.", ephemeral=True)
        return

    target_id = str(유저.id)
    current_balance = get_balance(target_id)
    
    # 2. 1000칩으로 맞추기 위한 차액 계산 후 반영
    diff = 1000 - current_balance
    update_balance(target_id, diff)

    await interaction.response.send_message(f"🧹 **{유저.display_name}**님의 잔고가 **1000** 칩으로 초기화되었습니다.")


if __name__ == "__main__":
    if not TOKEN:
        print("에러: .env 파일에 DISCORD_TOKEN이 설정되지 않았습니다.")
    else:
        bot.run(TOKEN)

