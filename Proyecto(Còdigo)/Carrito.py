#install Firmata
import pyfirmata2
import threading
import msvcrt
import time
import os

# --- Variables Globales ---
board = None
sensor1 = None
sensor2 = None
servo = None
alarm = None
HARDWARE_CONNECTED = False
running = True

# Estado simulado (se usa si el hardware no está conectado)
computers = [True, True]
alarm_state = False
alarm_thread = None

def simulation_input_loop():
    """
    En modo simulado, lee la consola para cambiar el estado de los sensores.
    Formato: 'computadora estado' (ej: '1 0' para decir que la PC 1 no está)
    """
    print("\n--- MODO SIMULACIÓN ACTIVO ---")
    print("Para cambiar el estado de un sensor, escribí en la consola y presioná Enter:")
    print("  '1 1' -> PC 1 presente")
    print("  '1 0' -> PC 1 ausente")
    print("  '2 1' -> PC 2 presente")
    print("  '2 0' -> PC 2 ausente")
    print("--------------------------------\n")
    
    global computers
    while running:
        try:
            line = input()
            parts = line.strip().split()
            if len(parts) == 2:
                pc_num, state = int(parts[0]), int(parts[1])
                if pc_num in [1, 2] and state in [0, 1]:
                    index = pc_num - 1
                    computers[index] = bool(state)
                    print(f"[Simulado] Estado de la Computadora {pc_num} actualizado a: {'Presente' if computers[index] else 'Ausente'}")
        except (ValueError, IndexError):
            # Ignora entradas inválidas para no detener el hilo
            pass
        except (EOFError, KeyboardInterrupt):
            break

# --- Inicialización del Hardware ---
try:
    PORT = pyfirmata2.ArduinoMega.AUTODETECT
    board = pyfirmata2.ArduinoMega(PORT)
    HARDWARE_CONNECTED = True
    print("[Hardware] Arduino conectado exitosamente.")
except Exception as e:
    print("[Hardware WARN] No se pudo conectar con Arduino. El programa se ejecutará en modo simulado.")
    print(f"[Hardware WARN] Razón: {e}")

def is_hardware_connected():
    """Devuelve True si el hardware (Arduino) está conectado."""
    return HARDWARE_CONNECTED

def Login(value):
    if value == 1:
        #Abrir el servo
        Open_cart()
        rta = int(input("\nQue computadora desea consultar? "))
        Verify_slot(rta)
    elif value == 2:
        #Cerrar el servo
        Close_cart()
        print("Adios :)")
        return

def get_computers():
    return computers

def set_computers(array):
    global computers
    computers = array

def Update_sensor1(value):
    global computers
    computers[0] = bool(value)

def Update_sensor2(value):
    global computers
    computers[1] = bool(value)

def Computer_state(index):
    global computers
    return computers[index]

def set_Computer_state(index, value):
    global computers
    computers[index] = value

def turn_to(degree):
    """Mueve el Servo a una direccion especifica"""
    if not HARDWARE_CONNECTED:
        print(f"[Simulado] Moviendo servo a {degree} grados.")
        return
    servo.write(degree)


def Open_cart():
    """Mueve el servo a 90 grados (posición abierta)"""
    if HARDWARE_CONNECTED:
        servo.write(180)


def Close_cart():
    """Mueve el servo a 0 grados (posición cerrada)"""
    if HARDWARE_CONNECTED:
        servo.write(0)

def alarm_loop():
    """Bucle del hilo del pitido"""
    global alarm_state
    while alarm_state:
        alarm.write(1)
        time.sleep(0.8)
        alarm.write(0)
        # pitido cada 0.8 segundos
        for _ in range(8):
            if not alarm_state:
                break
            time.sleep(0.1)


def Turn_alarm():
    """Activa el hilo del pitido si no está activo"""
    global alarm_state, alarm_thread
    if not HARDWARE_CONNECTED:
        print("[Simulado] Alarma activada.")
        return
    if not alarm_state:
        alarm_state = True
        alarm_thread = threading.Thread(target=alarm_loop, daemon=True)
        alarm_thread.start()

def Turn_on_alarm():
    """Enciende el pitido inmediatamente"""
    if not HARDWARE_CONNECTED:
        print("[Simulado] Alarma encendida.")
        return
    alarm_state = True
    alarm_thread = threading.Thread(target=alarm_loop, daemon=True)
    alarm_thread.start()

def Turn_off_alarm():
    """Apaga el pitido inmediatamente"""
    if not HARDWARE_CONNECTED:
        print("[Simulado] Alarma apagada.")
        return
    global alarm_state
    alarm_state = False
    alarm.write(0)


def Verify_slot(slot):
    """Verifica el estado de un slot y activa la alarma si la PC no está."""
    os.system('cls' if os.name == 'nt' else 'clear')
    # Corregido: Usar el 'slot' que se pasa a la función, no una variable global 'rta'.
    # Recordar que los índices de la lista empiezan en 0 (PC 1 -> índice 0).
    if not Computer_state(slot - 1):
        Turn_alarm()
        print(f"COMPUTADORA {slot} DESAPARECIDA!!")
    else:
        print(f"COMPUTADORA {slot} DEVUELTA")
        Turn_off_alarm()

def iterate_board():
    while running:
        if HARDWARE_CONNECTED:
            try:
                board.iterate()
                time.sleep(0.1)
            except Exception as e:
                print(f"[Hardware Error] Error en el bucle de iteración: {e}")
                break
        else:
            # Si no hay hardware, el hilo de iteración no necesita hacer nada,
            # ya que el hilo de simulación se encarga de la entrada.
            time.sleep(1)

def start_hardware():
    """Inicializa el hilo de lectura y mantiene conexión con Arduino."""
    global running
    if HARDWARE_CONNECTED:
        global sensor1, sensor2, servo, alarm
        
        # --- CONFIGURACIÓN DE PINES ---
        # ¡¡¡CAMBIA ESTOS NÚMEROS PARA QUE COINCIDAN CON TU ARDUINO!!!
        PIN_SENSOR_1 = 27  # Pin para el sensor de la Computadora 1
        PIN_SENSOR_2 = 26  # Pin para el sensor de la Computadora 2
        PIN_SERVO    = 2   # Pin para el servomotor
        PIN_ALARMA   = 53  # Pin para la alarma (buzzer)
        # ---------------------------------

        sensor1 = board.digital[PIN_SENSOR_1]
        sensor1.mode = pyfirmata2.INPUT
        sensor1.register_callback(Update_sensor1)
        sensor1.enable_reporting()

        sensor2 = board.digital[PIN_SENSOR_2]
        sensor2.mode = pyfirmata2.INPUT
        sensor2.register_callback(Update_sensor2)
        sensor2.enable_reporting()

        servo = board.digital[PIN_SERVO]
        servo.mode = pyfirmata2.SERVO
        alarm = board.digital[PIN_ALARMA]
        print("[Hardware] Pines configurados.")

    else: # Si estamos en modo simulado
        sim_thread = threading.Thread(target=simulation_input_loop, daemon=True)
        sim_thread.start()

    running = True
    t = threading.Thread(target=iterate_board, daemon=True)
    t.start()
    print("[Hardware] Arduino iniciado y sensores activos.")

def stop_hardware():
    """Detiene hilos y cierra la conexión con el Arduino."""
    global running
    running = False
    if HARDWARE_CONNECTED:
        Turn_off_alarm()
        board.exit()
        print("[Hardware] Conexión con Arduino cerrada.")
