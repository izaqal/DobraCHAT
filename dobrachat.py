import asyncio
import os
import mimetypes
import sys
from datetime import datetime
import aiohttp
from aiohttp_socks import ProxyConnector
from nio import (
    AsyncClient, 
    RoomMessage, 
    RoomMessageFile, 
    RoomMessageImage, 
    RoomMessageAudio, 
    RoomMessageVideo, 
    MatrixRoom, 
    RoomVisibility, 
    RoomPreset,
    RoomSendError,
    RoomBanError,
    RoomUnbanError,
    InviteMemberEvent
)
from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Input, RichLog, Static, Button

soru1 = input("Proxy seçiniz (TOR için T, I2P için I): ").strip().upper()
soru2 = input("Bağlanılacak Adres (örn. xyz.onion veya abc.b32.i2p): ").strip()
soru3 = input("Kullanıcı adınız: ").strip().lower()
soru4 = input("Şifreniz: ").strip()
soru5 = input("Sunucu adı: ").strip()

if soru1 not in ["T", "I"]:
    print("Hatalı bir girişte bulundunuz, lütfen T veya I seçiniz.")
    sys.exit(1)

PROXY_TYPE = soru1
HOMESERVER_URL = f"http://{soru2}"
SERVER_NAME = soru5
USER_ID = f"@{soru3}:{SERVER_NAME}"
PASSWORD = soru4

class MatrixTUI(App):
    TITLE = "DobraCHAT - Qal tarafından yapıldı"

    BINDINGS = [
        ("f2", "toggle_left", "Odalar"),
        ("f3", "toggle_right", "Kişiler"),
        ("ctrl+q", "quit", "Çıkış"),
    ]

    CSS = """
    Screen { background: #1e1e1e; color: #d4d4d4; }
    #left-sidebar { width: 25%; background: #252526; border-right: heavy #333333; padding: 1; }
    #chat-area { width: 1fr; padding: 1; } 
    #right-sidebar { width: 25%; background: #252526; border-left: heavy #333333; padding: 1; }
    #messages { height: 1fr; border: solid #333333; background: #1e1e1e; }
    #input-box { dock: bottom; height: 3; background: #2d2d2d; color: #ffffff; border: solid #007acc; }
    #top-bar { height: 3; margin-bottom: 1; align: center middle; }
    Button { margin-right: 1; min-width: 12; height: 3; background: #007acc; color: #ffffff; }
    Button:hover { background: #005999; }
    """

    def __init__(self):
        super().__init__()
        self.client = None
        self.current_room_id = None
        self.is_logged_in = False
        self.room_messages = {}

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal():
            with Vertical(id="left-sidebar"):
                yield Static("Odalar", classes="title")
                yield RichLog(id="room-list", highlight=True, markup=True)
            
            with Vertical(id="chat-area"):
                with Horizontal(id="top-bar"):
                    yield Button("◀ Odalar", id="btn-left")
                    yield Button("Kişiler ▶", id="btn-right")
                yield RichLog(id="messages", highlight=True, markup=True)
                yield Input(placeholder="Giriş bekleniyor...", id="input-box")
            
            with Vertical(id="right-sidebar"):
                yield Static("Kişiler", classes="title")
                yield RichLog(id="user-list", highlight=True, markup=True)
                
        yield Footer()

    def action_toggle_left(self) -> None:
        sidebar = self.query_one("#left-sidebar")
        sidebar.display = not sidebar.display

    def action_toggle_right(self) -> None:
        sidebar = self.query_one("#right-sidebar")
        sidebar.display = not sidebar.display

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-left":
            self.action_toggle_left()
        elif event.button.id == "btn-right":
            self.action_toggle_right()

    def on_mount(self) -> None:
        self.connect_to_matrix()

    def format_user_id(self, target: str) -> str:
        target = target.strip()
        if not target.startswith("@"):
            target = f"@{target}"
        if ":" not in target:
            target = f"{target}:{SERVER_NAME}"
        return target

    def render_chat_window(self) -> None:
        messages_widget = self.query_one("#messages", RichLog)
        messages_widget.clear()

        if not self.current_room_id:
            messages_widget.write("[dim]Aktif oda seçilmedi.[/dim]")
            return

        room = self.client.rooms.get(self.current_room_id) if self.client else None
        room_name = room.display_name if room else self.current_room_id
        messages_widget.write(f"[bold green]=== Aktif Oda: {room_name} ===[/bold green]")

        history = self.room_messages.get(self.current_room_id, [])
        for msg in history:
            messages_widget.write(msg)

    def update_ui_lists(self) -> None:
        self.update_room_list_ui()
        self.update_user_list_ui()

    def update_room_list_ui(self) -> None:
        room_list_widget = self.query_one("#room-list", RichLog)
        room_list_widget.clear()
        
        if not self.client or not self.client.rooms:
            room_list_widget.write("[dim]Oda yok[/dim]")
            return

        for room_id, room in self.client.rooms.items():
            name = room.display_name if room.display_name else room_id
            if room_id == self.current_room_id:
                room_list_widget.write(f"[bold green]> {name}[/bold green]\n  [dim cyan]{room_id}[/dim cyan]")
            else:
                room_list_widget.write(f"  {name}\n  [dim cyan]{room_id}[/dim cyan]")

    def update_user_list_ui(self) -> None:
        user_list_widget = self.query_one("#user-list", RichLog)
        user_list_widget.clear()

        if not self.client or not self.current_room_id:
            user_list_widget.write("[dim]Oda seçilmedi[/dim]")
            return

        room = self.client.rooms.get(self.current_room_id)
        if not room:
            user_list_widget.write("[dim]Kişiler alınamadı[/dim]")
            return

        for user_id, user in room.users.items():
            name = user.display_name if user.display_name else user_id.split(":")[0].lstrip("@")
            is_self = " (Sen)" if user_id == self.client.user_id else ""
            user_list_widget.write(f"  • {name}{is_self}")

    async def on_message_received(self, room: MatrixRoom, event: RoomMessage) -> None:
        body = getattr(event, "body", "") or event.source.get("content", {}).get("body", "")

        if body.startswith("!SYS:"):
            parts = body.split(":", 2)
            if len(parts) == 3:
                style = parts[1]
                msg_text = parts[2]
                timestamp = datetime.fromtimestamp(event.server_timestamp / 1000.0).strftime("%H:%M:%S") if getattr(event, "server_timestamp", None) else datetime.now().strftime("%H:%M:%S")
                time_prefix = f"[dim white][{timestamp}][/dim white] "
                formatted_msg = f"{time_prefix}[{style}]{msg_text}[/{style}]"

                if room.room_id not in self.room_messages:
                    self.room_messages[room.room_id] = []
                self.room_messages[room.room_id].append(formatted_msg)

                if room.room_id == self.current_room_id:
                    messages_widget = self.query_one("#messages", RichLog)
                    messages_widget.write(formatted_msg)
                return

        if event.sender == self.client.user_id:
            return

        sender_alias = event.sender.split(":")[0].lstrip("@")
        timestamp = datetime.fromtimestamp(event.server_timestamp / 1000.0).strftime("%H:%M:%S") if getattr(event, "server_timestamp", None) else datetime.now().strftime("%H:%M:%S")
        time_prefix = f"[dim white][{timestamp}][/dim white] "

        msgtype = getattr(event, "msgtype", None) or event.source.get("content", {}).get("msgtype")
        mxc_url = getattr(event, "url", None) or event.source.get("content", {}).get("url", None)

        if isinstance(event, (RoomMessageFile, RoomMessageImage, RoomMessageAudio, RoomMessageVideo)) or msgtype in ["m.file", "m.image", "m.audio", "m.video"]:
            mxc_str = f"\n  [bold green]İndirme Adresi:[/bold green] [bold cyan]{mxc_url}[/bold cyan]" if mxc_url else ""
            formatted_msg = (
                f"{time_prefix}[bold cyan]{sender_alias}:[/bold cyan][bold yellow]Dosya Gönderdi:[/bold yellow] {event.body}{mxc_str}"
            )
        else:
            formatted_msg = f"{time_prefix}[bold cyan]{sender_alias}:[/bold cyan] {event.body}"

        if room.room_id not in self.room_messages:
            self.room_messages[room.room_id] = []
        self.room_messages[room.room_id].append(formatted_msg)

        if room.room_id == self.current_room_id:
            messages_widget = self.query_one("#messages", RichLog)
            messages_widget.write(formatted_msg)

    async def on_invite_received(self, room: MatrixRoom, event: InviteMemberEvent) -> None:
        if event.state_key == self.client.user_id:
            messages_widget = self.query_one("#messages", RichLog)
            messages_widget.write(f"[yellow]Oda daveti alındı ({room.room_id}), otomatik katılınıyor...[/yellow]")
            await self.client.join(room.room_id)
            self.current_room_id = room.room_id
            self.render_chat_window()
            self.update_ui_lists()

    @work(exclusive=True)
    async def connect_to_matrix(self) -> None:
        messages_widget = self.query_one("#messages", RichLog)
        input_widget = self.query_one("#input-box", Input)

        messages_widget.write(f"[yellow]Sunucuya bağlanılıyor... ({USER_ID})[/yellow]")

        try:
            if PROXY_TYPE == "I":
                self.client = AsyncClient(HOMESERVER_URL, USER_ID, proxy="http://127.0.0.1:4444")
            elif PROXY_TYPE == "T":
                connector = ProxyConnector.from_url("socks5://127.0.0.1:9050")
                session = aiohttp.ClientSession(connector=connector)
                self.client = AsyncClient(HOMESERVER_URL, USER_ID)
                self.client.client_session = session

            self.client.add_event_callback(self.on_message_received, RoomMessage)
            self.client.add_event_callback(self.on_invite_received, InviteMemberEvent)

            resp = await asyncio.wait_for(
                self.client.login(PASSWORD),
                timeout=60.0
            )

            if hasattr(resp, "access_token") and resp.access_token is not None:
                self.is_logged_in = True
                messages_widget.write("[green]Giriş başarılı![/green]")
                input_widget.placeholder = "Mesaj yazın veya /help yazın..."

                while self.is_logged_in:
                    try:
                        await self.client.sync(timeout=30000, full_state=False)

                        if self.client.rooms and not self.current_room_id:
                            self.current_room_id = list(self.client.rooms.keys())[0]
                            self.render_chat_window()

                        self.update_ui_lists()
                        await asyncio.sleep(1)

                    except Exception as sync_err:
                        messages_widget.write(f"[yellow]Sync uyarısı: {sync_err}[/yellow]")
                        await asyncio.sleep(5)
            else:
                messages_widget.write(f"[red]Giriş başarısız: {resp}[/red]")

        except asyncio.TimeoutError:
            messages_widget.write("[red]Hata: Bağlantı zaman aşımına uğradı.[/red]")
        except Exception as e:
            messages_widget.write(f"[red]Bağlantı Hatası: {type(e).__name__} - {e}[/red]")

    @work
    async def do_send_message(self, room_id: str, text: str) -> None:
        messages_widget = self.query_one("#messages", RichLog)
        time_prefix = f"[dim white][{datetime.now().strftime('%H:%M:%S')}][/dim white] "
        try:
            res = await asyncio.wait_for(
                self.client.room_send(
                    room_id=room_id,
                    message_type="m.room.message",
                    content={"msgtype": "m.text", "body": text}
                ),
                timeout=60.0
            )
            
            if isinstance(res, RoomSendError):
                messages_widget.write(f"[red]Mesaj gönderilemedi: {res.message}[/red]")
                return

            formatted_msg = f"{time_prefix}[bold blue]Sen:[/bold blue] {text}"

            if room_id not in self.room_messages:
                self.room_messages[room_id] = []
            self.room_messages[room_id].append(formatted_msg)

            if room_id == self.current_room_id:
                messages_widget.write(formatted_msg)

        except asyncio.TimeoutError:
            messages_widget.write("[red]Hata: Mesaj zaman aşımına uğradı.[/red]")
        except Exception as e:
            messages_widget.write(f"[red]Mesaj gönderilemedi: {e}[/red]")

    @work
    async def do_send_system_announcement(self, room_id: str, style: str, text: str) -> None:
        try:
            await self.client.room_send(
                room_id=room_id,
                message_type="m.room.message",
                content={"msgtype": "m.text", "body": f"!SYS:{style}:{text}"}
            )
        except Exception:
            pass

    @work
    async def do_set_power_level(self, room_id: str, target_user_id: str, level: int) -> None:
        messages_widget = self.query_one("#messages", RichLog)
        target = self.format_user_id(target_user_id)
        try:
            pl_resp = await asyncio.wait_for(
                self.client.room_get_state_event(room_id, "m.room.power_levels"),
                timeout=30.0
            )
            
            content = pl_resp.content if hasattr(pl_resp, "content") else {}
            if "users" not in content:
                content["users"] = {}

            content["users"][target] = level

            res = await asyncio.wait_for(
                self.client.room_put_state(
                    room_id=room_id,
                    event_type="m.room.power_levels",
                    content=content
                ),
                timeout=30.0
            )

            if hasattr(res, "event_id"):
                if level == 50:
                    self.do_send_system_announcement(room_id, "bold green", f"{target} kullanıcısına Mod/Yetki (50) verildi.")
                elif level == 100:
                    self.do_send_system_announcement(room_id, "bold green", f"{target} kullanıcısına Admin (100) yetkisi verildi.")
                elif level == 0:
                    self.do_send_system_announcement(room_id, "bold yellow", f"{target} kullanıcısının yetkisi alındı (0 seviyesine düşürüldü).")
                else:
                    self.do_send_system_announcement(room_id, "bold cyan", f"{target} kullanıcısının güç seviyesi {level} yapıldı.")
            else:
                messages_widget.write(f"[bold red]Etiketlediğiniz kişi bulunamadı veya sizden daha üst yetkilere sahip.[/bold red]")

        except Exception as e:
            messages_widget.write(f"[bold red]Etiketlediğiniz kişi bulunamadı veya sizden daha üst yetkilere sahip.[/bold red]")

    @work
    async def do_ban_user(self, room_id: str, target_user_id: str, reason: str = "") -> None:
        messages_widget = self.query_one("#messages", RichLog)
        target = self.format_user_id(target_user_id)
        try:
            res = await asyncio.wait_for(
                self.client.room_ban(room_id, target, reason=reason),
                timeout=60.0
            )
            if isinstance(res, RoomBanError):
                messages_widget.write(f"[bold red]Etiketlediğiniz kişi bulunamadı veya sizden daha üst yetkilere sahip.[/bold red]")
            else:
                self.do_send_system_announcement(room_id, "bold red", f"{target} odadan banlandı.")
                self.update_ui_lists()
        except Exception as e:
            messages_widget.write(f"[bold red]Etiketlediğiniz kişi bulunamadı veya sizden daha üst yetkilere sahip.[/bold red]")

    @work
    async def do_unban_user(self, room_id: str, target_user_id: str) -> None:
        messages_widget = self.query_one("#messages", RichLog)
        target = self.format_user_id(target_user_id)
        try:
            res = await asyncio.wait_for(
                self.client.room_unban(room_id, target),
                timeout=60.0
            )
            if isinstance(res, RoomUnbanError):
                messages_widget.write(f"[bold red]Etiketlediğiniz kişi bulunamadı veya sizden daha üst yetkilere sahip.[/bold red]")
            else:
                self.do_send_system_announcement(room_id, "bold green", f"{target} kullanıcısının banı kaldırıldı.")
                
                try:
                    pl_resp = await self.client.room_get_state_event(room_id, "m.room.power_levels")
                    if hasattr(pl_resp, "content"):
                        content = pl_resp.content
                        if "users" not in content:
                            content["users"] = {}
                        content["users"][target] = 0
                        await self.client.room_put_state(room_id, "m.room.power_levels", content)
                except Exception:
                    pass

                try:
                    await self.client.room_invite(room_id, target)
                    self.do_send_system_announcement(room_id, "dim green", f"{target} odaya davet edildi.")
                except Exception:
                    pass

                self.update_ui_lists()
        except Exception as e:
            messages_widget.write(f"[bold red]Etiketlediğiniz kişi bulunamadı veya sizden daha üst yetkilere sahip.[/bold red]")

    @work
    async def do_upload_file(self, room_id: str, file_path: str) -> None:
        messages_widget = self.query_one("#messages", RichLog)

        if not os.path.exists(file_path) or not os.path.isfile(file_path):
            messages_widget.write(f"[bold red]Hata: '{file_path}' dosyası bulunamadı![/bold red]")
            return

        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type:
            mime_type = "application/octet-stream"

        messages_widget.write(f"[yellow]Dosya yükleniyor... ({file_name} - {file_size} byte)[/yellow]")

        try:
            with open(file_path, "rb") as f:
                response, _ = await asyncio.wait_for(
                    self.client.upload(
                        f,
                        content_type=mime_type,
                        filename=file_name,
                        filesize=file_size
                    ),
                    timeout=180.0
                )

            if hasattr(response, "content_uri"):
                content_uri = response.content_uri
                content = {
                    "body": file_name,
                    "info": {
                        "size": file_size,
                        "mimetype": mime_type
                    },
                    "msgtype": "m.file",
                    "url": content_uri
                }

                await asyncio.wait_for(
                    self.client.room_send(
                        room_id=room_id,
                        message_type="m.room.message",
                        content=content
                    ),
                    timeout=60.0
                )

                time_prefix = f"[dim white][{datetime.now().strftime('%H:%M:%S')}][/dim white] "
                formatted_msg = (
                    f"{time_prefix}[bold blue]Sen (Dosya Gönderdin):[/bold blue]{file_name}\n"
                    f"  [bold green]İndirme Adresi:[/bold green] [bold cyan]{content_uri}[/bold cyan]"
                )
                if room_id not in self.room_messages:
                    self.room_messages[room_id] = []
                self.room_messages[room_id].append(formatted_msg)

                if room_id == self.current_room_id:
                    messages_widget.write(formatted_msg)
            else:
                messages_widget.write(f"[bold red]Dosya yükleme başarısız: {response}[/bold red]")

        except asyncio.TimeoutError:
            messages_widget.write("[red]Hata: Dosya yükleme zaman aşımına uğradı.[/red]")
        except Exception as e:
            messages_widget.write(f"[red]Dosya Gönderme Hatası: {e}[/red]")

    @work
    async def do_download_file(self, mxc_url: str, save_path: str = None) -> None:
        messages_widget = self.query_one("#messages", RichLog)
        messages_widget.write(f"[yellow]Dosya indiriliyor: {mxc_url}...[/yellow]")

        try:
            response = await asyncio.wait_for(
                self.client.download(mxc_url),
                timeout=180.0
            )

            if hasattr(response, "body"):
                filename = save_path or getattr(response, "filename", None) or "indirilen_dosya"
                with open(filename, "wb") as f:
                    f.write(response.body)

                messages_widget.write(f"[bold green]Dosya başarıyla kaydedildi: {filename}[/bold green]")
            else:
                messages_widget.write(f"[bold red]İndirme başarısız: {response}[/bold red]")

        except asyncio.TimeoutError:
            messages_widget.write("[red]Hata: İndirme zaman aşımına uğradı.[/red]")
        except Exception as e:
            messages_widget.write(f"[red]İndirme Hatası: {e}[/red]")

    @work
    async def do_create_room(self, room_name: str) -> None:
        messages_widget = self.query_one("#messages", RichLog)
        try:
            response = await asyncio.wait_for(
                self.client.room_create(
                    name=room_name,
                    visibility=RoomVisibility.public,
                    preset=RoomPreset.public_chat
                ),
                timeout=60.0
            )
            if hasattr(response, "room_id"):
                self.current_room_id = response.room_id
                self.render_chat_window()
                messages_widget.write(f"[bold green]Oda oluşturuldu: {room_name}[/bold green]")
                messages_widget.write(f"[bold yellow]KATILIM ID'Sİ:[/bold yellow] [bold cyan]{response.room_id}[/bold cyan]")
                self.update_ui_lists()
            else:
                messages_widget.write(f"[red]Oda oluşturulamadı: {response}[/red]")
        except asyncio.TimeoutError:
            messages_widget.write("[red]Hata: Oda oluşturma zaman aşımına uğradı.[/red]")
        except Exception as e:
            messages_widget.write(f"[red]Hata: {e}[/red]")

    @work
    async def do_join_room(self, room_target: str) -> None:
        messages_widget = self.query_one("#messages", RichLog)
        try:
            response = await asyncio.wait_for(
                self.client.join(room_target),
                timeout=60.0
            )
            if hasattr(response, "room_id"):
                self.current_room_id = response.room_id
                await self.client.sync(timeout=5000, full_state=True)
                self.render_chat_window()
                messages_widget.write(f"[bold green]Odaya katılındı: {response.room_id}[/bold green]")
                self.update_ui_lists()
            else:
                messages_widget.write(f"[red]Odaya katılınamadı: {response}[/red]")
        except asyncio.TimeoutError:
            messages_widget.write("[red]Hata: Odaya katılma zaman aşımına uğradı.[/red]")
        except Exception as e:
            messages_widget.write(f"[red]Hata: {e}[/red]")

    @work
    async def do_leave_room(self, room_id: str) -> None:
        messages_widget = self.query_one("#messages", RichLog)
        try:
            response = await asyncio.wait_for(
                self.client.room_leave(room_id),
                timeout=60.0
            )
            if not hasattr(response, "status_code") or getattr(response, "status_code", 200) == 200:
                messages_widget.write(f"[bold yellow]Odadan ayrılındı: {room_id}[/bold yellow]")
                if room_id in self.room_messages:
                    del self.room_messages[room_id]
                if room_id in self.client.rooms:
                    del self.client.rooms[room_id]

                if self.current_room_id == room_id:
                    remaining_rooms = list(self.client.rooms.keys())
                    self.current_room_id = remaining_rooms[0] if remaining_rooms else None
                    self.render_chat_window()

                self.update_ui_lists()
            else:
                messages_widget.write(f"[red]Odadan ayrılınamadı: {response}[/red]")
        except asyncio.TimeoutError:
            messages_widget.write("[red]Hata: Odadan ayrılma zaman aşımına uğradı.[/red]")
        except Exception as e:
            messages_widget.write(f"[red]Hata: {e}[/red]")

    def switch_to_room_by_name(self, target_name: str) -> bool:
        for r_id, room in self.client.rooms.items():
            if target_name.lower() in room.display_name.lower() or target_name == r_id:
                self.current_room_id = r_id
                self.render_chat_window()
                self.update_ui_lists()
                return True
        return False

    def on_input_submitted(self, message: Input.Submitted) -> None:
        text = message.value.strip()
        message_widget = self.query_one("#messages", RichLog)
        input_widget = self.query_one("#input-box", Input)

        if not text or not self.is_logged_in:
            return

        input_widget.value = ""

        if text == "/help":
            message_widget.write("[bold yellow]Genel Komutlar:[/bold yellow]")
            message_widget.write("  [cyan]/upload <dosya_yolu>[/cyan] - Odaya dosya/resim yükler")
            message_widget.write("  [cyan]/download <mxc_url> [kayit_adi][/cyan] - Dosyayı indirir")
            message_widget.write("  [cyan]/create <oda_adi>[/cyan] - Oda oluşturur")
            message_widget.write("  [cyan]/join <oda_id_veya_alias>[/cyan] - Odaya katılır")
            message_widget.write("  [cyan]/switch <oda_adi_veya_id>[/cyan] - Başka odaya geçer")
            message_widget.write("  [cyan]/leave [oda_adi_veya_id][/cyan] - Odadan ayrılır")
            message_widget.write("  [cyan]/id[/cyan] - Aktif oda ID'sini gösterir")
            message_widget.write("[bold yellow]Yönetim Komutları:[/bold yellow]")
            message_widget.write("  [cyan]/op <kullanici_id> [seviye][/cyan] - Kullanıcıya yetki verir (Varsayılan: 50)")
            message_widget.write("  [cyan]/deop <kullanici_id>[/cyan] - Kullanıcının yetkisini alır (0 yapar)")
            message_widget.write("  [cyan]/ban <kullanici_id> [sebep][/cyan] - Kullanıcıyı banlar")
            message_widget.write("  [cyan]/unban <kullanici_id>[/cyan] - Kullanıcının banını kaldırır")
            return

        if text.startswith("/upload ") or text.startswith("/sendfile "):
            parts = text.split(" ", 1)
            file_path = parts[1].strip()
            if not self.current_room_id:
                message_widget.write("[red]Dosya yüklemek için önce bir odaya geçin![/red]")
                return
            self.do_upload_file(self.current_room_id, file_path)
            return

        if text.startswith("/download "):
            parts = text.split(" ", 2)
            mxc_url = parts[1].strip()
            save_path = parts[2].strip() if len(parts) > 2 else None

            if not mxc_url.startswith("mxc://"):
                message_widget.write("[red]Geçersiz adres! Adres 'mxc://...' şeklinde olmalı.[/red]")
                return

            self.do_download_file(mxc_url, save_path)
            return

        if text == "/id":
            if self.current_room_id:
                message_widget.write(f"[bold yellow]Mevcut Oda ID:[/bold yellow] [bold cyan]{self.current_room_id}[/bold cyan]")
            else:
                message_widget.write("[bold red]Aktif seçili oda yok![/bold red]")
            return

        if text.startswith("/create "):
            room_name = text.replace("/create ", "").strip()
            self.do_create_room(room_name)
            return

        if text.startswith("/switch "):
            target = text.replace("/switch ", "").strip()
            if not self.switch_to_room_by_name(target):
                message_widget.write(f"[red]Oda bulunamadı: '{target}'[/red]")
            return

        if text == "/leave" or text.startswith("/leave "):
            target = text.replace("/leave", "").strip()
            room_to_leave = None

            if not target:
                room_to_leave = self.current_room_id
            else:
                for r_id, room in self.client.rooms.items():
                    if target.lower() in room.display_name.lower() or target == r_id:
                        room_to_leave = r_id
                        break

            if not room_to_leave:
                message_widget.write(f"[red]Ayrılınacak oda bulunamadı: '{target}'[/red]")
                return

            self.do_leave_room(room_to_leave)
            return

        if text.startswith("/join "):
            room_target = text.replace("/join ", "").strip()
            if self.switch_to_room_by_name(room_target):
                return

            if not room_target.startswith("!") and not room_target.startswith("#"):
                message_widget.write("[red]Geçersiz oda formatı! '!id:domain' veya '#alias:domain' olmalı.[/red]")
                return
                
            self.do_join_room(room_target)
            return

        if text.startswith("/op "):
            parts = text.split(" ")
            target_user = parts[1]
            level = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 50
            self.do_set_power_level(self.current_room_id, target_user, level)
            return

        if text.startswith("/deop "):
            target_user = text.replace("/deop ", "").strip()
            self.do_set_power_level(self.current_room_id, target_user, 0)
            return

        if text.startswith("/ban "):
            parts = text.split(" ", 2)
            target_user = parts[1]
            reason = parts[2] if len(parts) > 2 else ""
            self.do_ban_user(self.current_room_id, target_user, reason)
            return

        if text.startswith("/unban "):
            target_user = text.replace("/unban ", "").strip()
            self.do_unban_user(self.current_room_id, target_user)
            return

        if not self.current_room_id:
            message_widget.write("[red]Aktif oda yok! '/switch <oda_adi>' ile bir odaya geçin.[/red]")
            return

        self.do_send_message(self.current_room_id, text)

    async def action_quit(self) -> None:
        self.is_logged_in = False
        if self.client:
            try:
                await self.client.close()
            except Exception:
                pass
        self.exit()

if __name__ == "__main__":
    app = MatrixTUI()
    app.run()
