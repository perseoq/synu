# Synu v1.0 

Inicializa el proyecto (crea .sync/)
```sh
synu init
```

Primer respaldo (guarda ruta del USB automáticamente)
```sh
synu backup -p /media/usb -m "Inicio del proyecto"
``` 

Respaldos siguientes ya no requieren -p
```sh
synu backup -m "Modificaciones nuevas"
```

Restaurar último respaldo
```sh
synu restore
```

Restaurar versión específica
```sh
synu downgrade -s gatitos_20250608_153000.zip
```
