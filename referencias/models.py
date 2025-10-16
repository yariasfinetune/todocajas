from django.db import models


class Referencia(models.Model):
    nombre = models.CharField(max_length=255)
    foto = models.ImageField(upload_to='fotos/')

    def __str__(self):
        return self.nombre

class Caja(models.Model):
    referencia = models.ForeignKey(Referencia, on_delete=models.CASCADE)
    ancho_cm = models.IntegerField()
    alto_cm = models.IntegerField()
    profundidad_cm = models.IntegerField()
    archivo_cdr = models.FileField(upload_to='cdr_files/')

    def __str__(self):
        return self.referencia.nombre + " - " + str(self.ancho_cm) + "x" + str(self.alto_cm) + "x" + str(self.profundidad_cm)