from pyrogram import Client

api_id = 29198449
api_hash = "1531c036b518574425d437a31d7480a1"

# Use a temporary session name so it prompts you for login
app = Client("my_session", api_id=api_id, api_hash=api_hash)

app.start()  # <-- This will ask for your phone number and code in console
print("\n\nYour Session String:\n")
print(app.export_session_string())
app.stop()
SESSION_STRING="BAG9iHEAAShliD8M5_2UnkfWWeDNOBPg1kTHQRO5ICDj7hBzk0zb4HZwcMXGLLualWAvPbxiivCjsqqEmyYSAF5JpTffZClgz87aPYalo2jqh61yvzeoaqbULu404iPIVogDEz4XlnR2ksVtZL8AUH-BYqJmkj1-UZpg1ZAmAuEnXO4rHtfv99urw5PPSA2TnDwcvI1pMKSCASrGzU7F7fmZvgtxJe3fb4ThX8FHOPwDx4RnQTd..."  
