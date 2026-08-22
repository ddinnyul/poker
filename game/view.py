import discord
from storage.balance import update_balance

# ==========================================
# 1. 레이즈 금액을 직접 입력받는 모달 창
# ==========================================
class RaiseInputModal(discord.ui.Modal, title="🔥 얼마나 레이즈할지 입력해 주세요"):
    raise_amount = discord.ui.TextInput(
        label="베팅할 총 칩 개수",
        placeholder="예: 40 (현재 최소 레이즈 금액 이상이어야 해요!)",
        required=True,
        min_length=1,
        max_length=7
    )

    def __init__(self, game, view_instance, interaction_user):
        super().__init__()
        self.game = game
        self.view_instance = view_instance
        self.user = interaction_user

    async def on_submit(self, interaction: discord.Interaction):
        player = self.game.get_current_player()
        
        # 1. 입력값 숫자 검증
        try:
            target_amount = int(self.raise_amount.value)
        except ValueError:
            await interaction.response.send_message("❌ 숫자만 입력해 주세요!", ephemeral=True)
            return

        # 2. 텍사스 홀덤 규칙에 맞는 최소 레이즈 금액 계산 (현재 최고 베팅의 최소 2배)
        min_raise = max(self.game.current_bet * 2, 20)  # 최소 베팅 기본선 20칩
        if target_amount < min_raise:
            await interaction.response.send_message(f"❌ 레이즈 금액이 너무 낮아요! 최소 **{min_raise}**칩 이상 베팅해야 합니다.", ephemeral=True)
            return

        # 3. 유저가 낼 수 있는 칩인지 확인
        needed_chip = target_amount - player.current_bet
        if player.chips < needed_chip:
            await interaction.response.send_message(f"❌ 보유한 칩이 부족해요! (현재 가진 칩: {player.chips}개)", ephemeral=True)
            return

        # 4. 베팅 상태 반영
        player.chips -= needed_chip
        player.current_bet = target_amount
        self.game.pot += needed_chip
        self.game.current_bet = target_amount
        self.game.last_raiser_id = player.user_id
        
        update_balance(player.user_id, -needed_chip)
        
        if player.chips == 0:
            player.is_all_in = True

        self.game.action_counter += 1
        
        await interaction.response.send_message(f"🔥 **{player.username}**님이 판돈을 **{target_amount}칩**으로 크게 올렸습니다! (레이즈)", ephemeral=False)
        await self.view_instance.process_next_step(interaction)


# ==========================================
# 2. 메인 베팅 뷰 클래스
# ==========================================
class PokerBettingView(discord.ui.View):
    def __init__(self, game, bot_instance, update_embed_func):
        super().__init__(timeout=None)
        self.game = game
        self.bot = bot_instance
        self.update_embed = update_embed_func

    async def verify_turn(self, interaction: discord.Interaction):
        current_player = self.game.get_current_player()
        if str(interaction.user.id) != current_player.user_id:
            await interaction.response.send_message("🤫 현재는 다른 사람의 차례입니다 😡", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="체크 (넘기기)", style=discord.ButtonStyle.secondary, custom_id="poker_check")
    async def check_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.verify_turn(interaction): return
        player = self.game.get_current_player()
        if player.current_bet < self.game.current_bet:
            await interaction.response.send_message("❌ 턴을 그냥 넘길 수 없습니다.", ephemeral=True)
            return
        self.game.action_counter += 1
        await interaction.response.send_message(f"✅ **{player.username}**님이 체크했습니다.", ephemeral=False)
        await self.process_next_step(interaction)

    @discord.ui.button(label="콜 (맞추기)", style=discord.ButtonStyle.success, custom_id="poker_call")
    async def call_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.verify_turn(interaction): return
        player = self.game.get_current_player()
        call_amount = self.game.current_bet - player.current_bet
        if call_amount <= 0:
            await interaction.response.send_message("❌ 현재 받아쳐야 할 칩이 없습니다. '체크'를 눌러주세요.", ephemeral=True)
            return
        actual_call = min(player.chips, call_amount)
        player.chips -= actual_call
        player.current_bet += actual_call
        self.game.pot += actual_call
        update_balance(player.user_id, -actual_call)
        if player.chips == 0: player.is_all_in = True
        self.game.action_counter += 1
        await interaction.response.send_message(f"💰 **{player.username}**님이 **{actual_call}칩 콜**.", ephemeral=False)
        await self.process_next_step(interaction)

    @discord.ui.button(label="레이즈 (키우기)", style=discord.ButtonStyle.primary, custom_id="poker_raise")
    async def raise_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.verify_turn(interaction): return
        # 같은 파일 내부이므로 프롬프트 다이렉트로 연동 처리
        modal = RaiseInputModal(self.game, self, interaction.user)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="💥 올인 (All-in!)", style=discord.ButtonStyle.primary, row=1, custom_id="poker_allin")
    async def all_in_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.verify_turn(interaction): return
        player = self.game.get_current_player()
        if player.chips <= 0:
            await interaction.response.send_message("❌ 더 이상 내세울 칩이 없습니다.", ephemeral=True)
            return
        
        all_in_chips = player.chips
        player.current_bet += all_in_chips
        self.game.pot += all_in_chips
        player.chips = 0
        player.is_all_in = True
        
        if player.current_bet > self.game.current_bet:
            self.game.current_bet = player.current_bet
            self.game.last_raiser_id = player.user_id
            
        update_balance(player.user_id, -all_in_chips)
        self.game.action_counter += 1
        
        await interaction.response.send_message(f"💥 🔥 **{player.username}**님 **{all_in_chips}칩 올인**", ephemeral=False)
        await self.process_next_step(interaction)

    @discord.ui.button(label="폴드 (기권)", style=discord.ButtonStyle.danger, row=1, custom_id="poker_fold")
    async def fold_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.verify_turn(interaction): return
        player = self.game.get_current_player()
        player.has_folded = True
        self.game.action_counter += 1
        await interaction.response.send_message(f"🏳️ **{player.username}**님이 폴드했습니다.", ephemeral=False)
        await self.process_next_step(interaction)

    async def process_next_step(self, interaction: discord.Interaction):
        """베팅 종료 시 봇이 판단하여 다음 카드를 자동으로 깔아줍니다."""
        if self.game.is_betting_round_over():
            is_showdown = self.game.advance_phase()
            
            if is_showdown:
                embed = discord.Embed(
                    title="🏁 모든 베팅 라운드 종료! (Showdown)",
                    description=f"승자확인타임~~!!😡🎊🎉💕💕🤝\n누적된 총 상금 팟: **{self.game.pot}** 칩",
                    color=0x2ecc71
                )
                self.clear_items()
                await interaction.message.edit(view=self)
                await interaction.channel.send(embed=embed)
            else:
                self.clear_items()
                try:
                    await interaction.message.edit(view=self)
                except:
                    pass
                
                new_view = PokerBettingView(self.game, self.bot, self.update_embed)
                await self.update_embed(interaction.channel, new_view)
        else:
            self.game.next_turn()
            await self.update_embed(interaction.channel, self)

    # game/view.py 파일 맨 위에 main 모듈의 함수를 가져올 수 있도록 임포트문을 추가하거나,
# process_next_step 내부에서 바로 호출할 수 있도록 구조를 수정합니다.

    async def process_next_step(self, interaction: discord.Interaction):
        """베팅 종료 시 봇이 판단하여 다음 카드를 깔거나 최종 승자 정산을 트리거합니다."""
        if self.game.is_betting_round_over():
            is_showdown = self.game.advance_phase()
            
            if is_showdown:
                # [수정 포인트] 딱딱한 예고장 대신, 메인 모듈의 쇼다운 엔진을 즉시 연동하여 실행합니다.
                self.clear_items()
                await interaction.message.edit(view=self)
                
                # 순환 임포트를 피하기 위해 함수 내부에서 main의 process_showdown을 호출합니다.
                from main import process_showdown
                await process_showdown(interaction.channel, self.game)
            else:
                self.clear_items()
                try:
                    await interaction.message.edit(view=self)
                except:
                    pass
                
                new_view = PokerBettingView(self.game, self.bot, self.update_embed)
                await self.update_embed(interaction.channel, new_view)
        else:
            self.game.next_turn()
            await self.update_embed(interaction.channel, self)

