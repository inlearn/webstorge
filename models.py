from django.db import models
from django.conf import settings


# Create your models here.

class FileInfo(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=True)
    file_path = models.CharField(max_length=128, verbose_name='存储路径')
    file_name = models.CharField(max_length=128, verbose_name='文件名')
    update_time = models.DateTimeField(verbose_name='上传时间')
    file_type = models.CharField(max_length=32, verbose_name='文件类型')
    file_size = models.CharField(max_length=16, verbose_name='文件大小')
    belong_folder = models.CharField(max_length=64, verbose_name='所属文件夹')


class FolderInfo(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=True)
    update_time = models.DateTimeField(verbose_name='创建时间')
    belong_folder = models.CharField(max_length=64, verbose_name='所属文件夹')
    folder_name = models.CharField(max_length=64, verbose_name='文件夹名')
