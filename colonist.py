import asyncio
from pyppeteer import launch
import json
import constant as const
import base64
import ast
import msgpack
import os
import subprocess
from pywinauto import Application
import pyautogui
import numpy as np
import time

# write_board_to_txt: writes board data from unpacked msg to text files
def write_board_to_txt(data):
    tiles_data = data['data']['payload']['tileState']['tiles']

    with open('hexes.txt', 'w') as f:
        for tile in tiles_data:
            f.write(str(const.TILE_TYPES[tile["tileType"]]) + " ")
    
    with open('dice.txt', 'w') as f:
        for tile in tiles_data:
            f.write(str(tile["_diceNumber"]) + " ")

    ports_data = data['data']['payload']['portState']['portEdges']
    
    with open('ports.txt', 'w') as f:
        for port in ports_data:
            f.write(str(const.PORT_TYPES[port['portType'] - 1]) + " ")

def unpack_msg(s):
    if str(s).startswith("gq"):
        return str(msgpack.unpackb(base64.b64decode(str(s))))
    return str(s)

def unpack_board(s):
    string = unpack_msg(s)
    if "hex" in string:
        data = ast.literal_eval(string)
        write_board_to_txt(data)
        
        current_directory = os.getcwd()
        server_command = ['java', '-Ddir=' + current_directory, '-Djsettlers.bots.fast_-pause_percent=10', '-jar', 'JSettlersServer-2.7.00.jar']
        client_command = ['java', '-Ddir=' + current_directory, '-jar', 'JSettlers-2.7.00.jar', 'localhost', '8880']
        subprocess.Popen(server_command)
        for i in range(4):
            subprocess.Popen(client_command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
        
    return False
    
def handle_websocket_frame(params, frame_received_event):
    # Extract the payload data
    global payload
    payload = params.get('response', {}).get('payloadData', '')

    # Set the event
    frame_received_event.set()

async def capture_websocket_frames(url='https://example.com'):
    # Create an asyncio.Event instance
    frame_received_event = asyncio.Event()
    
    browser = await launch(headless=False, executablePath=r'C:\Program Files\Google\Chrome\Application\chrome.exe', args=[
        '--window-size=650,620',
        '--window-position=-170,-265'
    ])
    page = (await browser.pages())[0]

    # Create a CDP session
    client = await page.target.createCDPSession()

    # Enable necessary domains
    await client.send('Network.enable')

    # Setup event listeners for WebSocket frames
    # Adjust the lambda to set the event upon receiving a frame
    client.on('Network.webSocketFrameReceived', lambda params: handle_websocket_frame(params, frame_received_event))

    # Navigate to the target web page
    await page.goto(url)

    # Continuously wait for frames
    while True:
        await frame_received_event.wait()  # Wait for the event to be set

        global payload
        msg = unpack_msg(payload)

        if "'type': 8," in msg:
            order = ast.literal_eval(msg)['data']['payload']['playOrder']
            base = order.index(1)

        # type 16 indicates settlement placement
        if "'type': 16," in msg:
            if ast.literal_eval(msg)['data']['payload'][0]['owner'] != 1:
                window_index = adjust_index(order.index(ast.literal_eval(msg)['data']['payload'][0]['owner']), base)
                player_windows[window_index].set_focus()
                coords_dict = ast.literal_eval(msg)['data']['payload'][0]['hexCorner']
                place_settlement(coords_dict)

        global placements
        global awaiting_quit
        # type 15 indicates road placement
        if "'type': 15," in msg:
            if ast.literal_eval(msg)['data']['payload'][0]['owner'] != 1:
                window_index = adjust_index(order.index(ast.literal_eval(msg)['data']['payload'][0]['owner']), base)
                player_windows[window_index].set_focus()
                coords_dict = ast.literal_eval(msg)['data']['payload'][0]['hexEdge']
                place_road(coords_dict)

            placements += 1
        
        if placements >= 8 and awaiting_quit:
            quit_game(player_windows)
            awaiting_quit = False

        #if "'type': 59," in msg:
        #    input("Hit enter and then do in colonist.io what the robot did in JSettlers!")

        global awaiting_start
        if awaiting_start:
            if unpack_board(payload):
                time.sleep(3)
                player_windows = []
                for i in range(4):
                    app = Application().connect(title = "JSettlers client 2.7.00", found_index = i)
                    menu_window = app.windows()[0]
                    menu_window.maximize()
                    menu_window.set_focus()
                    pyautogui.click(const.NAME_BOX)
                    pyautogui.press(chr(ord('a') + i))
                    time.sleep(1)
                    if i == 0:
                        pyautogui.click(const.NEW_GAME)
                        time.sleep(1)
                        pyautogui.press('g')
                        pyautogui.press('enter')
                        time.sleep(1)
                        player_windows.append(app.windows()[0])
                    else:
                        pyautogui.click(const.JOIN_GAME)
                        if i < 3:
                            time.sleep(1)
                            player_windows.append(app.windows()[0])

                print("Player windows: " + str(len(player_windows)))
                for window in player_windows:
                    window.maximize()
                start_game(player_windows, order)
                awaiting_start = False
            
        frame_received_event.clear()  # Reset the event to wait for the next frame

def quit_game(player_windows):
    for i in range(3):
        player_windows[i].set_focus()
        pyautogui.click((np.array(const.PLAYER_COORDS[i]) + const.QUIT).tolist())
        time.sleep(1)
        pyautogui.click(const.QUIT_SURE)
    
def start_game(player_windows, order):
    # join each player to the game
    for i in range(3):
        player_windows[i].set_focus()
        pyautogui.click((np.array(const.PLAYER_COORDS[i]) + const.SIT_HERE).tolist())
        
    # check order, set starting player accordingly
    with open('start.txt', 'w') as f:
        start = (order.index(1) * 3) % 4
        f.write(str(start))

    # set focus to window of player 1
    player_windows[0].set_focus()
    # start game
    pyautogui.click((np.array(const.PLAYER_COORDS[0]) + const.START).tolist())
    order.remove(1)

def place_settlement(coords_dict):
    zero_hex = np.array(const.ZERO_COORDS[coords_dict['y']])
    hex = zero_hex + np.array([coords_dict['x'] * 80, 0])
    if coords_dict['z'] == 0:
        corner = hex + np.array([0, -47])
    else:
        corner = hex + np.array([0, 43])
    pyautogui.click(corner.tolist())

def place_road(coords_dict):
    zero_hex = np.array(const.ZERO_COORDS[coords_dict['y']])
    hex = zero_hex + np.array([coords_dict['x'] * 80, 0])
    if coords_dict['z'] == 0:
        edge = hex + np.array([-19, -37])
    elif coords_dict['z'] == 1:
        edge = hex + np.array([-40, 0])
    else:
        edge = hex + np.array([-19, 33])
    pyautogui.click(edge.tolist())

def adjust_index(index, base):
    if base == 0 or base == 3:
        return index
    elif base == 1:
        if index == 0:
            return 2
        return index - 1
    else:
        if index == 2:
            return 0
        return index + 1

awaiting_start = True
awaiting_quit = True
placements = 0
payload = ""
asyncio.run(capture_websocket_frames('https://colonist.io/'))