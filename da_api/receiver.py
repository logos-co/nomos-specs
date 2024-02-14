class Receiver:
    def __init__(self):
        pass

    def receive_chunk():
        # Receives from network new chunks to be processed.
        # TODO: use chunk inbound queue to receive.
        pass

    def receive_block():
        # Receives from blockchain latest blocks added.
        # TODO: use block inbound queue to receive.
        pass

    def write_to_cache(chunk, metadata):
        # Logic to write the chunk to cache.
        pass    

    def write_to_storage(certificate):
        # Logic to write data to storage based on the certificate.
        pass
