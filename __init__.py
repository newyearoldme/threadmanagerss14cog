from .threadmanagerss14cog import ThreadManagerCog

def setup(client):
    client.add_cog(ThreadManagerCog(client))
