import os
from django.db import models
from django.conf import settings
from scripts.get_bounding_box import get_bounding_box_mm
from .tasks import convert_cdr_to_pdf, convert_cdr_to_pdf_async


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
    archivo_pdf = models.FileField(upload_to='pdf_files/', null=True, blank=True)
    ancho_2d_mm = models.DecimalField(editable=False, blank=True, null=True, decimal_places=1, max_digits=10)
    alto_2d_mm = models.DecimalField(editable=False, blank=True, null=True, decimal_places=1, max_digits=10)

    def crear_archivo_pdf(self):
        """
        Crea el archivo PDF de la caja.
        """
        if not self.archivo_cdr:
            raise ValueError("No CDR file associated with this Caja instance")
        
        # Try Django's FileField .path property first
        try:
            cdr_file_path = self.archivo_cdr.path
            # Check if file exists at Django-expected location
            if os.path.exists(cdr_file_path):
                convert_cdr_to_pdf(self.pk, cdr_file_path)
                return
        except (ValueError, AttributeError):
            pass
        
        # Fallback: try legacy location (project root cdr_files/)
        filename = os.path.basename(self.archivo_cdr.name)
        base_dir = getattr(settings, 'BASE_DIR', None)
        if base_dir:
            legacy_path = os.path.join(str(base_dir), 'cdr_files', filename)
            if os.path.exists(legacy_path):
                convert_cdr_to_pdf(self.pk, legacy_path)
                return
        
        # If still not found, use the path property anyway (let it fail with clearer error)
        convert_cdr_to_pdf(self.pk, self.archivo_cdr.path)

    
    def calcular_ancho_alto_2d(self):
        """
        Calcula el bounding box de la caja en 2D.
        """
        if not self.archivo_pdf:
            raise ValueError("No PDF file associated with this Caja instance")
        
        bounding_box_width_mm, bounding_box_height_mm = get_bounding_box_mm(self.archivo_pdf.path)
        self.ancho_2d_cm = bounding_box_width_mm
        self.alto_2d_cm = bounding_box_height_mm
        self.save()

    def save(self, *args, **kwargs):
        """
        Calcula el ancho y alto en 2D de la caja.
        Triggers async conversion of CDR to PDF via CloudConvert API.
        """
        # Check if this is a new instance or if the CDR file has changed
        is_new = self.pk is None
        cdr_changed = False
        
        if not is_new:
            try:
                old_instance = Caja.objects.get(pk=self.pk)
                # Compare by file name to detect changes
                old_cdr_name = old_instance.archivo_cdr.name if old_instance.archivo_cdr else None
                new_cdr_name = self.archivo_cdr.name if self.archivo_cdr else None
                cdr_changed = old_cdr_name != new_cdr_name
            except Caja.DoesNotExist:
                is_new = True
        
        # Save the instance first to get the ID and ensure file is saved
        super().save(*args, **kwargs)
        
        # Trigger async conversion if we have a CDR file and it's new or changed
        if self.archivo_cdr and (is_new or cdr_changed):
            # Use Django's FileField .path property to get the absolute file path
            cdr_file_path = self.archivo_cdr.path
            convert_cdr_to_pdf_async(self.pk, cdr_file_path)

    def __str__(self):
        return self.referencia.nombre + " - " + str(self.ancho_cm) + "x" + str(self.alto_cm) + "x" + str(self.profundidad_cm)