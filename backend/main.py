from fastapi import FastAPI, File, Form, HTTPException, Request, Response, UploadFile,Depends
from sqlalchemy.orm import Session
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
import os
from storage import get_user, get_users,delete_user, add_user,update_user
from storage import get_areas
from storage import get_permission
from pydantic import BaseModel

from storage import get_db

from fastapi.middleware.cors import CORSMiddleware
from fastapi import Query


app = FastAPI()


# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permitir cualquier origen (puedes restringirlo)
    allow_credentials=True,
    allow_methods=["*"],  # Permitir todos los métodos (GET, POST, etc.)
    allow_headers=["*"],  # Permitir todos los headers
)

# Montar la carpeta estática para que FastAPI reconozca los archivos de estilo CSS
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "../frontend/static")), name="static")

# Montar la carpeta 'CarpetaInfo' como una carpeta estática para acceder a los archivos PDF
app.mount("/CarpetaInfo", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "../CarpetaInfo")), name="CarpetaInfo")
# Cargar la página de inicio de sesión
@app.get("/", response_class=HTMLResponse)
async def index():
    # Ruta del archivo HTML de inicio
    index_path = os.path.join(os.path.dirname(__file__), "../frontend/inicio.html")
    with open(index_path, "r", encoding="utf-8") as f:
        # Retornamos la respuesta en HTML
        return HTMLResponse(content=f.read(), status_code=200)

@app.post("/login", response_class=HTMLResponse)
async def login(request: Request, strUsuario: str = Form(...), strContrasenna: str = Form(...)):
    # Llamar a la función para obtener los datos del usuario
    user = get_user(strUsuario, strContrasenna)

    # Validar si el usuario existe
    if user is None:
        raise HTTPException(status_code=401, detail="Nombre de usuario o contraseña incorrectos")

    # Validar el permiso del usuario para redirigirlo
    id_permission = user["id_permission"]

    # Redirección según el permiso
    if id_permission == 1:  # Admin
        redirect_url = "/admin"
    elif id_permission == 2:  # Usuario normal
        redirect_url = "/viewer_downloader"
    elif id_permission == 3:  # Usuario normal
        redirect_url = "/viewer"
    else:
        raise HTTPException(status_code=403, detail="No tienes permiso para acceder a esta vista")

    # Redirigir a la vista correspondiente
    return RedirectResponse(url=redirect_url, status_code=303)


# RUTAS DE USUARIOS 


@app.get("/users", response_class=HTMLResponse)
async def list_users():
    # Obtener los usuarios usando la función de storage.py
    users = get_users()

    # Leer el archivo HTML
    template_path = os.path.join(os.path.dirname(__file__), "../frontend/usersTable.html")
    with open(template_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    # Inyectar los datos de los usuarios en el HTML
    table_rows = ""
    for user in users:
        table_rows += f"""
            <tr>
                <td>{user['username']}</td>
                <td>{user['email']}</td>
                <td>{user['id_permission']}</td>
                <td>{user['id_area']}</td>
                <td>
                    <button class="edit-btn" onclick="editUser({user['id']})">Editar</button>
                    <button class="delete-btn" onclick="deleteUser({user['id']})">Eliminar</button>
                </td>
            </tr>
        """
    
    # Reemplazamos el marcador en el HTML con las filas generadas
    html_content = html_content.replace("<!-- rows-placeholder -->", table_rows)

    return HTMLResponse(content=html_content)


@app.get("/usersJSON")
async def list_users():
    # Crear la conexión a la base de datos
    connection = get_db()
    cursor = connection.cursor(dictionary=True)

    # Consulta SQL para obtener los usuarios
    query = """
        SELECT id, str_name_user AS username, str_email AS email, id_permission, id_area
        FROM tbl_users
    """
    cursor.execute(query)
    users = cursor.fetchall()

    # Cerrar la conexión a la base de datos
    cursor.close()
    connection.close()

    # Retornar los usuarios en formato JSON
    return JSONResponse(content={"users": users})




@app.get("/users_paginated", response_class=JSONResponse)
async def list_users_paginated(page: int = Query(1, alias="page"), per_page: int = Query(10, alias="per_page")):
    """
    Obtiene la lista de usuarios con paginación.
    """
    # Crear la conexión a la base de datos
    connection = get_db()
    cursor = connection.cursor(dictionary=True)

    # Consulta SQL para obtener el total de usuarios y la paginación
    query = """
        SELECT id, str_name_user AS username, str_email AS email, id_permission, id_area
        FROM tbl_users
        LIMIT %s OFFSET %s
    """
    
    # Calcular el índice de inicio (OFFSET) y el número de usuarios por página (LIMIT)
    offset = (page - 1) * per_page
    cursor.execute(query, (per_page, offset))
    users = cursor.fetchall()

    # Consulta para obtener el número total de usuarios
    cursor.execute("SELECT COUNT(*) FROM tbl_users")
    total_users = cursor.fetchone()["COUNT(*)"]

    # Cerrar la conexión a la base de datos
    cursor.close()
    connection.close()

    # Calcular el número total de páginas
    total_pages = (total_users + per_page - 1) // per_page  # Redondeo hacia arriba
    
    return {
        "users": users,
        "total_users": total_users,
        "current_page": page,
        "per_page": per_page,
        "total_pages": total_pages  # Retornar el total de páginas
    }

@app.get("/users_search", response_class=JSONResponse)
async def search_users(query: str = Query(..., alias="query")):
    """
    Busca usuarios por nombre o correo sin paginación.
    """
    connection = get_db()
    cursor = connection.cursor(dictionary=True)

    search_query = """
        SELECT id, str_name_user AS username, str_email AS email, id_permission, id_area
        FROM tbl_users
        WHERE LOWER(str_name_user) LIKE %s OR LOWER(str_email) LIKE %s
    """
    
    cursor.execute(search_query, (f"%{query.lower()}%", f"%{query.lower()}%"))
    users = cursor.fetchall()

    cursor.close()
    connection.close()

    return {"users": users}

@app.delete("/users/{user_id}")
async def delete_user_route(user_id: int):
    # Llamar a la función de eliminación de usuario
    print(f"Intentando eliminar el usuario con ID: {user_id}")
    success = delete_user(user_id)

    if success:
        # Si el usuario se eliminó con éxito, devolver un mensaje de éxito
        return JSONResponse(status_code=200, content={"message": "Usuario eliminado exitosamente"})
    else:
        # Si no se encontró el usuario o ocurrió algún error, devolver un mensaje de error
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

        
    

# Modelo Pydantic para los datos de entrada del usuario
class UserCreate(BaseModel):
    str_name_user: str
    str_email: str
    str_password: str
    id_permission: int
    id_area: int


# Endpoint para crear el usuario
@app.post("/users/")
async def create_user(user: UserCreate):
    try:
        # Llamar a la función para agregar el usuario a la base de datos
        result = add_user(user.str_name_user, user.str_email, user.str_password, user.id_permission, user.id_area)

        # Verificar el resultado de la función add_user
        if result["success"]:
            return JSONResponse(status_code=201, content={"message": result["message"]})
        else:
            raise HTTPException(status_code=400, detail=result["message"])

    except Exception as e:
        # Si ocurre un error inesperado, devolver un error 500
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")
    
def get_user_by_id(user_id: int, db: Session):
    try:
        query = "SELECT * FROM users WHERE id = %s"
        db.execute(query, (user_id,))
        user = db.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
    

# Modelo Pydantic para la actualización de datos del usuario
class UserUpdate(BaseModel):
    str_name_user: str
    str_email: str
    str_password: str
    id_permission: int
    id_area: int

# Función para actualizar los datos del usuario
def update_user(id: int, name: str, email: str, password: str, id_permission: int, id_area: int, db: Session):
    try:
        # Si la contraseña no está vacía, puedes agregar lógica para encriptarla
        # Puedes usar librerías como bcrypt para la encriptación aquí
        query = """
            UPDATE tbl_users
            SET str_name_user = %s, str_email = %s, str_password = %s, id_permission = %s, id_area = %s
            WHERE id = %s
        """
        db.execute(query, (name, email, password, id_permission, id_area, id))
        db.commit()
        
        return {"success": True, "message": "Usuario actualizado exitosamente"}
    except Exception as e:  
        db.rollback()
        return {"success": False, "message": f"Error: {str(e)}"}    

@app.put("/users/{id}")
async def update_user_endpoint(id: int, user_data: UserUpdate, db: Session = Depends(get_db)):
    result = update_user(id, user_data.str_name_user, user_data.str_email, user_data.str_password, user_data.id_permission, user_data.id_area, db)
    
    if result["success"]:
        return {"message": result["message"]}
    else:
        raise HTTPException(status_code=400, detail=result["message"])  









# RUTAS DE AREAS


@app.get("/areas", response_class=HTMLResponse)
async def list_areas():
    # Obtener los usuarios usando la función de storage.py
    areas = get_areas()

    # Leer el archivo HTML
    template_path = os.path.join(os.path.dirname(__file__), "../frontend/areaTable.html")
    with open(template_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    # Inyectar los datos de los usuarios en el HTML
    table_rows = ""
    for area in areas:
        table_rows += f"""
            <tr>
                <td>{area['nameArea']}</td>
                <td>{area['description']}</td>
                <td>
                    <button class="edit-btn" onclick="editArea({area['id']})">Editar</button>
                    <button class="delete-btn" onclick="deleteArea({area['id']})">Eliminar</button>
                </td>
            </tr>
        """
    
    # Reemplazamos el marcador en el HTML con las filas generadas
    html_content = html_content.replace("<!-- rows-placeholder -->", table_rows)

    return HTMLResponse(content=html_content)


@app.get("/areas_paginated", response_class=JSONResponse)
async def list_areas_paginated(page: int = Query(1, alias="page"), per_page: int = Query(10, alias="per_page")):
    """
    Obtiene la lista de areas con paginación.
    """
    # Crear la conexión a la base de datos
    connection = get_db()
    cursor = connection.cursor(dictionary=True)

    # Consulta SQL para obtener el total de usuarios y la paginación
    query = """
        SELECT id, str_name_area AS nameArea, str_description AS description
        FROM tbl_areas
        LIMIT %s OFFSET %s
    """
    
    # Calcular el índice de inicio (OFFSET) y el número de areas por página (LIMIT)
    offset = (page - 1) * per_page
    cursor.execute(query, (per_page, offset))
    areas = cursor.fetchall()

    # Consulta para obtener el número total de areas
    cursor.execute("SELECT COUNT(*) FROM tbl_areas")
    total_areas = cursor.fetchone()["COUNT(*)"]

    # Cerrar la conexión a la base de datos
    cursor.close()
    connection.close()

    # Calcular el número total de páginas
    total_pages = (total_areas + per_page - 1) // per_page  # Redondeo hacia arriba
    
    return {
        "areas": areas,
        "total_areas": total_areas,
        "current_page": page,
        "per_page": per_page,
        "total_pages": total_pages  # Retornar el total de páginas
    }

@app.get("/areas_search", response_class=JSONResponse)
async def search_permissions(query: str = Query(..., alias="query")):
    """
    Busca areas por nombre o correo sin paginación.
    """
    connection = get_db()
    cursor = connection.cursor(dictionary=True)

    search_query = """
        SELECT id, str_name_area AS nameArea, str_description AS description
        FROM tbl_areas
        WHERE LOWER(str_name_area) LIKE %s OR LOWER(str_description) LIKE %s
    """
    
    cursor.execute(search_query, (f"%{query.lower()}%", f"%{query.lower()}%"))
    areas = cursor.fetchall()

    cursor.close()
    connection.close()

    return {"areas": areas}


# RUTAS DE PERMISOS 

@app.get("/permissions", response_class=HTMLResponse)
async def list_permissions():
    # Obtener los permisos usando la función de storage.py
    permissions = get_permission()

    # Leer el archivo HTML
    template_path = os.path.join(os.path.dirname(__file__), "../frontend/permissionTable.html")
    with open(template_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    # Inyectar los datos de los usuarios en el HTML
    table_rows = ""
    for permission in permissions:
        table_rows += f"""
            <tr>
                <td>{permission['namePermission']}</td>
                <td>{permission['description']}</td>
                <td>
                    <button class="edit-btn" onclick="editPermission({permission['id']})">Editar</button>
                    <button class="delete-btn" onclick="deletePermission({permission['id']})">Eliminar</button>
                </td>
            </tr>
        """
    
    # Reemplazamos el marcador en el HTML con las filas generadas
    html_content = html_content.replace("<!-- rows-placeholder -->", table_rows)

    return HTMLResponse(content=html_content)


@app.get("/permissions_paginated", response_class=JSONResponse)
async def list_permissions_paginated(page: int = Query(1, alias="page"), per_page: int = Query(10, alias="per_page")):
    """
    Obtiene la lista de permisos con paginación.
    """
    # Crear la conexión a la base de datos
    connection = get_db()
    cursor = connection.cursor(dictionary=True)

    # Consulta SQL para obtener el total de permisos y la paginación
    query = """
        SELECT id, str_name_permission AS namePermission, str_description AS description
        FROM tbl_permissions
        LIMIT %s OFFSET %s
    """
    
    # Calcular el índice de inicio (OFFSET) y el número de permisos por página (LIMIT)
    offset = (page - 1) * per_page
    cursor.execute(query, (per_page, offset))
    permissions = cursor.fetchall()

    # Consulta para obtener el número total de permisos
    cursor.execute("SELECT COUNT(*) FROM tbl_permissions")
    total_permissions = cursor.fetchone()["COUNT(*)"]

    # Cerrar la conexión a la base de datos
    cursor.close()
    connection.close()

    # Calcular el número total de páginas
    total_pages = (total_permissions + per_page - 1) // per_page  # Redondeo hacia arriba
    
    return {
        "permissions": permissions,
        "total_permissions": total_permissions,
        "current_page": page,
        "per_page": per_page,
        "total_pages": total_pages  # Retornar el total de páginas
    }


@app.get("/permissions_search", response_class=JSONResponse)
async def search_permissions(query: str = Query(..., alias="query")):
    """
    Busca permisos por nombre o correo sin paginación.
    """
    connection = get_db()
    cursor = connection.cursor(dictionary=True)

    search_query = """
        SELECT id, str_name_permission AS namePermission, str_description AS description
        FROM tbl_permissions
        WHERE LOWER(str_name_permission) LIKE %s OR LOWER(str_description) LIKE %s
    """
    
    cursor.execute(search_query, (f"%{query.lower()}%", f"%{query.lower()}%"))
    permissions = cursor.fetchall()

    cursor.close()
    connection.close()

    return {"permissions": permissions}








# Vista para permisos de administrador
@app.get("/admin")
async def view_admin():
    # Cargar la página HTML para el administrador
    admin_page_path = os.path.join(os.path.dirname(__file__), "../frontend/viewAdmin.html")
    with open(admin_page_path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read(), status_code=200)
    

    
# Vista para permisos de visualización y descarga
@app.get("/viewer_downloader")
async def view_viewer_download():
    #Cargar la página HTML para descargar y ver el pdf
    viewer_download_page_path = os.path.join(os.path.dirname(__file__), "../frontend/viewViewerDownloader.html")
    with open(viewer_download_page_path,"r",encoding="utf-8") as f:
        return HTMLResponse(content=f.read(),status_code=200) 
         

    
# Vista para permisos de visualización
@app.get("/viewer")
async def view_viewer():
    # Cargar la página HTML para el viewer
    viewer_page_path = os.path.join(os.path.dirname(__file__), "../frontend/viewViewer.html")
    with open(viewer_page_path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read(), status_code=200)

    
# Ruta para eliminar archivos de la carpeta (rol de admin)
@app.delete("/files/{filename}")
async def delete_file(filename: str):
    folder_path = os.path.join(os.path.dirname(__file__), "../CarpetaInfo")
    file_path = os.path.join(folder_path, filename)

    if os.path.exists(file_path):
        os.remove(file_path)
        return {"message": f"Archivo '{filename}' eliminado correctamente."}
    else:
        raise HTTPException(status_code=404, detail="No se encontró el archivo a eliminar.")


# Endpoint para obtener los archivos PDF
@app.get("/api/get-files")
async def get_files():
    try:
        # Ruta a la carpeta donde están los archivos PDF
        folder_path = os.path.join(os.path.dirname(__file__), "../CarpetaInfo")
        
        # Verificar si la carpeta existe
        if not os.path.exists(folder_path):
            raise HTTPException(status_code=404, detail="Carpeta no encontrada")
        
        # Obtener lista de archivos de la carpeta
        files = os.listdir(folder_path)
        
        # Filtrar solo los archivos .pdf
        pdf_files = [file for file in files if file.endswith(".pdf")]
        
        # Si no hay archivos PDF
        if not pdf_files:
            raise HTTPException(status_code=404, detail="No se encontraron archivos PDF")
        
        # Retornar los nombres de los archivos PDF
        return JSONResponse(content={"files": pdf_files})
    
    except Exception as e:
        # En caso de error, mostrar un mensaje adecuado
        raise HTTPException(status_code=500, detail=str(e))


# FUNCION PARA PODER ENRUTAR POR ROL 
@app.get("/verdocumentos", response_class=HTMLResponse)
async def ver_carpeta(request: Request):
    user_role = request.headers.get("role")
    print(f"Rol recibido en /verdocumentos: {user_role}")  # Esto imprimirá el valor del rol recibido

    if user_role == "admin":
        view_path = os.path.join(os.path.dirname(__file__), "../frontend/viewAdmin.html")
    elif user_role == "viewer_downloader":
        view_path = os.path.join(os.path.dirname(__file__), "../frontend/viewViewerDownloader.html")
    elif user_role == "viewer":
        view_path = os.path.join(os.path.dirname(__file__), "../frontend/viewViewer.html")
    else:
        raise HTTPException(status_code=403, detail="Rol no válido o no autorizado")
    
    with open(view_path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read(), status_code=200)


    
    # # Leer y retornar el archivo HTML correspondiente
    # with open(view_path, "r", encoding="utf-8") as f:
    #     return HTMLResponse(content=f.read(), status_code=200)

# Ruta para manejar el logout y redirigir al login
@app.post("/logout")
async def logout(response: Response):
    # Eliminar la cookie de sesión
    response.delete_cookie("session") 
    
    # Redirigir al login
    return RedirectResponse(url="/", status_code=303)

# Ruta para subir archivos (rol de admin)
@app.post("/files/upload")
async def upload_file(request: Request, file: UploadFile= File(...)):
    # user_role = request.headers.get("Role")
    # if user_role != 'admin':
    #     raise HTTPException(status_code=403, detail="No tienes permisos para subir archivos.")
    
    folder_path = os.path.join(os.path.dirname(__file__),"../CarpetaInfo")
    file_path = os.path.join(folder_path, file.filename)
    
    with open(file_path,"wb") as f:
        f.write(await file.read())
    return{"message": f"Archivo '{file.filename}' subido correctamente a la carpeta."}


# Ruta para descargar archivos y visualizar (admin y viewer_downloader)
@app.get("/files/{file_name}")
async def download_file(file_name:str, request: Request):
    user_role = request.headers.get("Role")
    if user_role not in ["admin", "viewer_downloader"]:
        raise HTTPException(status_code=403, detail="Solo tienes permisos de visualización.")
    
    folder_path = os.path.join(os.path.dirname(__file__), "../CarpetaInfo")
    file_path = os.path.join(folder_path, file_name)

    if os.path.exists(file_path):
        return FileResponse(file_path, media_type='application/pdf', filename=file_name)
    else:
        raise HTTPException(status_code=404, detail="Archivo no encontrado")