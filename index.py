# coding: utf-8
import eel
import sys
import serial.tools.list_ports
import time
import json
import platform
import tkinter as tk
import tkinter.filedialog
import tkinter.messagebox
import pypandoc
import os
import webbrowser

# Enumeração de Status
class SerialStatus:
    Ready = 0
    Busy = 2

serial_port = None
serial_status = SerialStatus.Ready
filename = ""
app_options = {
    'comport':'COM1',
    'nbcol':27,
    'nbline':20,
    'brailletbl':70,
    'lang':''
}

# --- AJUSTE PARA LINUX: Removido winreg ---
def check_chrome_linux():
    # No Linux, geralmente verificamos se o binário existe no PATH
    import shutil
    chrome_names = ['chromium', 'google-chrome-stable', 'google-chrome', 'chromium-browser']
    for name in chrome_names:
        if shutil.which(name):
            print(f"Navegador encontrado: {name}")
            return True
    return False

def remove_comment(string):
    if string.find(';') == -1: return string
    return string[:string.index(';')]

def save_parameters():
    try:
        with open('parameters.json', 'w', encoding='utf-8') as of:
            json.dump(app_options, of)
    except Exception as e: print(e)

def load_parameters():
    try:
        if os.path.exists('parameters.json'):
            with open('parameters.json', 'r', encoding='utf-8') as inf:
                data = json.load(inf)
                for k,v in data.items():
                    if k in app_options: app_options[k] = v
    except Exception as e: print(e)

# --- EXPOSIÇÃO DE FUNÇÕES PARA O REACT (EEL) ---
@eel.expose
def gcode_set_parameters(opt):
    try:
        for k,v in opt.items():
            if k in app_options: app_options[k] = v
        save_parameters()
    except Exception as e: print(e)

@eel.expose
def gcode_get_parameters():
    return json.dumps(app_options)

@eel.expose
def printer_get_status():
    return serial_status

@eel.expose
def load_file(dialogtitle, filterstring):
    global filename
    js = {"data":"", "error":""}
    root = tk.Tk()
    root.withdraw() # Esconde a janela principal do TK
    fname = tkinter.filedialog.askopenfilename(title=dialogtitle)
    root.destroy()
    if fname:
        with open(fname, "rt", encoding='utf8') as inf:
            js["data"] = inf.read()
            filename = fname
    return json.dumps(js)

@eel.expose
def gcode_get_serial():
    data = []
    try:
        ports = serial.tools.list_ports.comports()
        for port in ports:
            data.append({'device':port.device, 'description':port.description, 'name':port.name, 'product':port.product, 'manufacturer':port.manufacturer})
    except Exception as e: print(e)
    return json.dumps(data)

@eel.expose
def PrintGcode(gcode, comport):
    global serial_status
    serial_status = SerialStatus.Busy
    print(f"Iniciando impressão em {comport}")
    # Lógica de porta serial simplificada para teste inicial
    time.sleep(2)
    serial_status = SerialStatus.Ready
    return " "

# --- INICIALIZAÇÃO ---
if __name__ == '__main__':
    print("App start no Arch Linux")

    if not check_chrome_linux():
        print("Erro: Chrome/Chromium não encontrado.")
        sys.exit(-1)

    load_parameters()

    # Tenta iniciar o Eel apontando para a pasta 'build' gerada pelo React
    if os.path.exists('build'):
        eel.init('build')
        print("Pasta 'build' detectada. Iniciando interface...")
        # No Linux, usamos host='localhost' para evitar problemas de rede
        eel.start('index.html', mode='chrome', host='localhost', port=8888)
    else:
        print("Erro: Pasta 'build' não encontrada. Rode 'npm run build' primeiro.")
