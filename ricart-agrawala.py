from mpi4py import MPI
import random
import time

# Constantes
REQUEST = 0
PERMISSION = 1
PROB_ACCESS = 30

# Inicialización MPI
comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()

# Variables globales
logical_clock = 0
request_timestamp = None
pending_requests = set()
received_permissions = 0
wants_to_enter = False

# Nuevo poema en español
poem = [
    "Este ", "es ", "un ", "mensaje ", "de ", "prueba ", "para ", "mostrar ", 
    "cómo ", "funciona ", "el ", "algoritmo ", "de ", "Ricart-Agrawala.", "\n\n"
]

def send_request():
    """
    Enviar solicitudes de acceso a la región crítica.
    """
    global logical_clock, request_timestamp, received_permissions, wants_to_enter
    wants_to_enter = True
    request_timestamp = logical_clock
    received_permissions = 0
    for process in range(size):
        if process != rank:
            comm.send([REQUEST, logical_clock, rank], dest=process)
            print(f"[{rank}] Enviando REQUEST a {process}")


def handle_request(sender, msg_clock):
    """
    Manejar una solicitud de otro proceso.
    """
    global logical_clock
    logical_clock = max(logical_clock, msg_clock + 1)

    if not wants_to_enter or (request_timestamp, rank) > (msg_clock, sender):
        # Conceder permiso inmediato
        comm.send([PERMISSION, logical_clock, rank], dest=sender)
        print(f"[{rank}] Enviando PERMISSION a {sender}")
    else:
        # Añadir a la lista de pendientes
        pending_requests.add(sender)
        print(f"[{rank}] Poniendo en espera a {sender}")


def handle_permission():
    """
    Manejar un permiso recibido.
    """
    global received_permissions
    received_permissions += 1
    if received_permissions == size - 1:  # Todos han dado permiso
        critical_section()
        release_critical_section()


def critical_section():
    """
    Región crítica: escritura en un archivo compartido.
    """
    global logical_clock
    print(f"[{rank}] Entrando a la región crítica")

    # Leer posición actual del poema
    try:
        with open("position.txt", "r") as f:
            position = int(f.read())
    except FileNotFoundError:
        position = 0

    # Escribir palabra en el poema
    with open("poem.txt", "a") as f:
        word = poem[position]
        f.write(word)
        print(f"[{rank}] Escribió: {word.strip()}")

    # Actualizar la posición
    position = (position + 1) % len(poem)
    with open("position.txt", "w") as f:
        f.write(str(position))

    time.sleep(random.uniform(0.1, 0.5))  # Simular trabajo


def release_critical_section():
    """
    Salir de la región crítica y responder a solicitudes pendientes.
    """
    global wants_to_enter, pending_requests
    print(f"[{rank}] Saliendo de la región crítica")

    wants_to_enter = False
    for process in pending_requests:
        comm.send([PERMISSION, logical_clock, rank], dest=process)
        print(f"[{rank}] Enviando PERMISSION pendiente a {process}")
    pending_requests.clear()


def main():
    global logical_clock

    while True:
        # Probabilidad de intentar entrar en la región crítica
        if random.randint(1, 100) <= PROB_ACCESS and not wants_to_enter:
            send_request()

        # Escuchar mensajes entrantes
        while comm.Iprobe(source=MPI.ANY_SOURCE):
            msg = comm.recv(source=MPI.ANY_SOURCE)
            msg_type, msg_clock, sender = msg
            logical_clock = max(logical_clock, msg_clock + 1)

            if msg_type == REQUEST:
                handle_request(sender, msg_clock)
            elif msg_type == PERMISSION:
                handle_permission()

        # Incrementar el reloj lógico
        logical_clock += 1
        time.sleep(0.01)  # Reducir carga del CPU


if __name__ == "__main__":
    main()
