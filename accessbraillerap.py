import os
import platform
import webview
import json
import sys
import serial
import serial.tools.list_ports
import time
import threading
from pathlib import Path

# Força o WebKit a ignorar erros de driver de vídeo e aceleração
os.environ['WEBKIT_DISABLE_COMPOSITING_MODE'] = '1'
os.environ['WEBKIT_FORCE_SANDBOX'] = '0'

app_options = {
    "comport": "COM1", "nbcol": "31", "nbline": "24", "brailletbl": "70",
    "lang": "", "theme": "light", "offsetx":"1", "offsety":"2.5", "pagewidthx":"75"
}

# Variável global para armazenar o último arquivo salvo
filename = ""

# Status da impressão
class SerialStatus:
    Ready = 0
    Busy = 1

serial_status = SerialStatus.Ready
print_cancel_flag = threading.Event()

class Api:
    def __init__(self, window=None):
        self.window = window
    
    def set_window(self, window):
        """Define a janela do webview para usar nos diálogos de arquivo"""
        self.window = window
    def gcode_get_parameters(self):
        print("React solicitou parâmetros")
        return json.dumps(app_options)

    def gcode_set_parameters(self, opt):
        """Atualiza os parâmetros da aplicação"""
        print(f"React está atualizando parâmetros: {opt}")
        try:
            # opt é um dicionário Python passado pelo pywebview
            if isinstance(opt, dict):
                for k, v in opt.items():
                    if k in app_options:
                        app_options[k] = v
                        print(f"  {k} = {v}")
            return True
        except Exception as e:
            print(f"Erro ao atualizar parâmetros: {e}")
            return False

    def gcode_get_serial(self):
        """Lista as portas seriais disponíveis no sistema"""
        print("React solicitou lista de portas")
        data = []
        try:
            ports = serial.tools.list_ports.comports()
            for port in ports:
                data.append({
                    "device": port.device,
                    "description": port.description or "",
                    "name": port.name or "",
                    "product": port.product or "",
                    "manufacturer": port.manufacturer or "",
                })
            print(f"Encontradas {len(data)} portas seriais")
        except Exception as e:
            print(f"Erro ao listar portas seriais: {e}")
            # Em caso de erro, ainda retorna lista vazia mas loga o erro
        
        # Se a porta configurada não estiver na lista, adiciona ela mesmo assim
        # Isso permite usar portas que não foram detectadas automaticamente
        if not any(d.get("device", "???") == app_options.get("comport", "") for d in data):
            configured_port = app_options.get("comport", "")
            if configured_port:
                print(f"Adicionando porta configurada que não foi detectada: {configured_port}")
                data.append({
                    "device": configured_port,
                    "description": "Configurada manualmente",
                    "name": configured_port,
                    "product": "",
                    "manufacturer": "",
                })
        
        return json.dumps(data)

    def printer_get_status(self):
        """Retorna o status da impressora"""
        global serial_status
        return serial_status

    def init_app(self):
        print(">>> JS chamou: init_app (Sinal de vida do React!)")
        return True

    def CancelPrint(self):
        """Cancela a impressão em andamento"""
        global print_cancel_flag, serial_status
        print("Cancelando impressão...")
        print_cancel_flag.set()
        serial_status = SerialStatus.Ready
        return True

    def PrintGcode(self, gcode, comport):
        """Envia G-code para a impressora via porta serial"""
        global serial_status, print_cancel_flag
        
        if serial_status == SerialStatus.Busy:
            print("Impressora ocupada")
            return "Impressão em andamento"
        
        # Reset cancel flag
        print_cancel_flag.clear()
        serial_status = SerialStatus.Busy
        
        try:
            print(f"Abrindo porta serial: {comport}")
            with serial.Serial(comport, 250000, timeout=2, write_timeout=2) as Printer:
                print(f"{comport} aberta")
                
                # Wake up printer
                Printer.write(b"\r\n\r\n")
                time.sleep(1)
                Printer.flushInput()
                
                print("Enviando G-code")
                gcodelines = gcode.split("\r\n")
                
                for line in gcodelines:
                    # Check if cancelled
                    if print_cancel_flag.is_set():
                        print("Impressão cancelada pelo usuário")
                        serial_status = SerialStatus.Ready
                        return "Impressão cancelada"
                    
                    cmd_gcode = self._remove_comment(line).strip()
                    
                    if cmd_gcode and not cmd_gcode.isspace():
                        print(f"Enviando: {cmd_gcode}")
                        Printer.write(cmd_gcode.encode() + b"\n")
                        
                        # Wait for "ok" response
                        tbegin = time.time()
                        while True:
                            if print_cancel_flag.is_set():
                                print("Impressão cancelada durante envio")
                                serial_status = SerialStatus.Ready
                                return "Impressão cancelada"
                            
                            grbl_out = Printer.readline()
                            if grbl_out:
                                print(grbl_out.strip().decode("utf-8", errors="ignore"))
                                if b"ok" in grbl_out:
                                    break
                                tbegin = time.time()
                            
                            if time.time() - tbegin > 5:
                                raise Exception("Timeout na comunicação com a impressora")
                
                print("Fim da impressão")
                serial_status = SerialStatus.Ready
                return " "
                
        except serial.SerialException as e:
            print(f"Erro de porta serial: {e}")
            serial_status = SerialStatus.Ready
            return f"Erro de porta serial: {str(e)}"
        except Exception as e:
            print(f"Erro na impressão: {e}")
            serial_status = SerialStatus.Ready
            return f"Erro de impressão: {str(e)}"
    
    def _remove_comment(self, line):
        """Remove comentários de uma linha G-code"""
        if ';' in line:
            return line.split(';')[0]
        return line

    def save_file(self, data, dialogtitle, filterstring):
        """Salva o arquivo. Se filename já existe, salva diretamente. Caso contrário, abre diálogo."""
        global filename
        
        if not self.window:
            self.window = webview.windows[0] if webview.windows else None
        
        if not self.window:
            print("Erro: Janela do webview não disponível")
            return False
        
        # Se não há filename salvo, abre diálogo
        if filename == "" or filename is None:
            try:
                # filterstring é uma lista: [filter_text, filter_generic]
                # pywebview espera uma tupla de strings no formato "Description (*.ext)"
                file_types = (
                    filterstring[0] + " (*.txt)",
                    filterstring[1] + " (*.*)"
                ) if len(filterstring) >= 2 else ("Text files (*.txt)", "All files (*.*)")
                
                fname = self.window.create_file_dialog(
                    webview.SAVE_DIALOG,
                    allow_multiple=False,
                    file_types=file_types
                )
                
                if not fname or fname == "":
                    return False
                filename = fname
            except Exception as e:
                print(f"Erro ao abrir diálogo de salvar: {e}")
                return False
        
        # Salva o arquivo
        try:
            with open(filename, "w", encoding="utf8") as f:
                f.write(data)
            print(f"Arquivo salvo: {filename}")
            return True
        except Exception as e:
            print(f"Erro ao salvar arquivo: {e}")
            return False

    def saveas_file(self, data, dialogtitle, filterstring):
        """Sempre abre diálogo para salvar como"""
        global filename
        
        if not self.window:
            self.window = webview.windows[0] if webview.windows else None
        
        if not self.window:
            print("Erro: Janela do webview não disponível")
            return False
        
        try:
            # filterstring é uma lista: [filter_text, filter_generic]
            # pywebview espera uma tupla de strings no formato "Description (*.ext)"
            file_types = (
                filterstring[0] + " (*.txt)",
                filterstring[1] + " (*.*)"
            ) if len(filterstring) >= 2 else ("Text files (*.txt)", "All files (*.*)")
            
            fname = self.window.create_file_dialog(
                webview.SAVE_DIALOG,
                allow_multiple=False,
                file_types=file_types
            )
            
            if not fname or fname == "":
                return False
            
            filename = fname
            
            with open(filename, "w", encoding="utf8") as f:
                f.write(data)
            print(f"Arquivo salvo como: {filename}")
            return True
        except Exception as e:
            print(f"Erro ao salvar arquivo: {e}")
            return False

    def load_file(self, dialogtitle, filterstring):
        """Abre diálogo para carregar arquivo e retorna JSON com dados"""
        global filename
        
        if not self.window:
            self.window = webview.windows[0] if webview.windows else None
        
        if not self.window:
            print("Erro: Janela do webview não disponível")
            return json.dumps({"data": "", "error": "Window not available"})
        
        js = {"data": "", "error": ""}
        
        # Verifica filtro
        if len(filterstring) < 2:
            js["error"] = "incorrect file filter"
            return json.dumps(js)
        
        try:
            # pywebview espera uma tupla de strings no formato "Description (*.ext)"
            file_types = (
                filterstring[0] + " (*.txt)",
                filterstring[1] + " (*.*)"
            )
            
            listfiles = self.window.create_file_dialog(
                webview.OPEN_DIALOG,
                allow_multiple=False,
                file_types=file_types
            )
            
            if not listfiles or len(listfiles) != 1:
                return json.dumps(js)
            
            fname = listfiles[0]
            if not fname or fname == "":
                return json.dumps(js)
            
            with open(fname, "rt", encoding="utf8") as f:
                js["data"] = f.read()
                filename = fname
            
            print(f"Arquivo carregado: {filename}")
            return json.dumps(js)
        except Exception as e:
            js["error"] = str(e)
            print(f"Erro ao carregar arquivo: {e}")
            return json.dumps(js)

    def import_pandoc(self, dialogtitle, filterstring):
        """Importa arquivo usando pandoc (se disponível)"""
        global filename
        
        if not self.window:
            self.window = webview.windows[0] if webview.windows else None
        
        if not self.window:
            print("Erro: Janela do webview não disponível")
            return json.dumps({"data": "", "error": "Window not available"})
        
        js = {"data": "", "error": ""}
        
        try:
            # pywebview espera uma tupla de strings
            file_types = (filterstring[0] + " (*.*)",) if len(filterstring) >= 1 else ("All files (*.*)",)
            
            listfiles = self.window.create_file_dialog(
                webview.OPEN_DIALOG,
                allow_multiple=False,
                file_types=file_types
            )
            
            if not listfiles or len(listfiles) != 1:
                return json.dumps(js)
            
            fname = listfiles[0]
            if not fname or fname == "":
                return json.dumps(js)
            
            filename = ""
            
            # Tenta usar pypandoc se disponível, senão apenas lê o arquivo como texto
            try:
                import pypandoc
                js["data"] = pypandoc.convert_file(
                    fname,
                    "plain+simple_tables",
                    extra_args=(),
                    encoding="utf-8",
                    outputfile=None,
                )
            except ImportError:
                # Se pypandoc não estiver disponível, apenas lê o arquivo como texto
                print("pypandoc não disponível, lendo arquivo como texto simples")
                with open(fname, "rt", encoding="utf8") as f:
                    js["data"] = f.read()
            except Exception as e:
                js["error"] = str(e)
                print(f"Erro ao converter arquivo com pandoc: {e}")
            
            filename = fname
            print(f"Arquivo importado: {filename}")
            return json.dumps(js)
        except Exception as e:
            js["error"] = str(e)
            print(f"Erro ao importar arquivo: {e}")
            return json.dumps(js)

def get_entrypoint():
    # Obtém o diretório do script (não depende do CWD)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    build_dir = os.path.join(base_dir, "build")
    index_path = os.path.join(build_dir, "index.html")
    
    # Verifica se o build existe
    if not os.path.exists(index_path):
        raise FileNotFoundError(f"Build não encontrado em: {index_path}")
    
    # Verifica se os arquivos estáticos existem
    static_dir = os.path.join(build_dir, "static")
    if not os.path.exists(static_dir):
        print(f"AVISO: Diretório static não encontrado em: {static_dir}")
    
    abs_index_path = os.path.abspath(index_path)
    abs_build_dir = os.path.abspath(build_dir)
    
    print(f"DEBUG: Script em: {base_dir}")
    print(f"DEBUG: Servindo diretório build de: {abs_build_dir}")
    print(f"DEBUG: HTML index em: {abs_index_path}")
    print(f"DEBUG: Static dir existe: {os.path.exists(static_dir)}")
    
    # Com http_server=True, passamos o arquivo index.html
    # O pywebview serve arquivos do diretório que contém o arquivo
    # Isso permite que os caminhos relativos (./static/js/...) funcionem
    return abs_index_path

if __name__ == "__main__":
    api = Api()
    base_dir = os.path.dirname(os.path.abspath(__file__))
    build_dir = os.path.join(base_dir, "build")
    
    # Muda para o diretório build para garantir que os caminhos relativos funcionem
    original_cwd = os.getcwd()
    try:
        os.chdir(build_dir)
        entry = "index.html"  # Caminho relativo do diretório build
        print(f"DEBUG: Mudando CWD para: {build_dir}")
        print(f"DEBUG: Usando entry: {entry}")
        
        # Com http_server=True, passamos o arquivo index.html
        # O pywebview serve arquivos do diretório atual (build)
        window = webview.create_window(
            "AccessBrailleRAP Debug", entry, js_api=api, width=1000, height=700
        )
        
        # Define a janela no API para usar nos diálogos de arquivo
        api.set_window(window)

        # http_server=True é OBRIGATÓRIO no Linux para o React carregar os JS
        # debug=True permite ver erros no console do navegador
        webview.start(gui="gtk", http_server=True, debug=True)
    finally:
        # Restaura o diretório original
        os.chdir(original_cwd)
