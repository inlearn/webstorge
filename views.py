from django.shortcuts import render, redirect
from .models import FileInfo, FolderInfo
from django.http import FileResponse, JsonResponse, HttpResponse
import os
from .untils import judge_filepath, format_size
from django.utils import timezone
from django.utils.http import urlquote
from django.contrib import auth
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.messages import info
import shutil
import os.path

# Create your views here.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARENT_DIR = os.path.abspath(os.path.join(BASE_DIR, "../"))


@login_required
def index(request):
    user = request.user
    user_id = User.objects.get(username=user).id
    file_obj = FileInfo.objects.filter(user_id=user_id, belong_folder='')
    folder_obj = FolderInfo.objects.filter(user_id=user_id, belong_folder='')
    index_list = []
    for file in file_obj:
        file.is_file = True
        index_list.append(file)
    for folder in folder_obj:
        folder.is_file = False
        index_list.append(folder)
    breadcrumb_list = [{'tag': '全部文件', 'uri': ''}]
    return render(request, 'webstroge/index.html',
                  {'index_list': index_list, 'username': str(user), 'breadcrumb_list': breadcrumb_list})


@login_required
def folder(request):
    # 收集用户id，要查看的目录信息，
    user = request.user
    user_id = User.objects.get(username=user).id
    pdir = request.GET.get('pdir')
    if pdir:
        if pdir[-1:] == '/':
            belong_folder = pdir
        else:
            belong_folder = pdir + '/'
    else:
        belong_folder = ''

    # 找出当前目录中的文件与文件夹信息
    file_obj = FileInfo.objects.filter(user_id=user_id, belong_folder=belong_folder)
    folder_obj = FolderInfo.objects.filter(user_id=user_id, belong_folder=belong_folder)
    index_list = []
    for file in file_obj:
        # 临时添加上是否为文件的标识
        file.is_file = True
        index_list.append(file)
    for folder in folder_obj:
        # 临时加上是否是文件的标识
        folder.is_file = False
        index_list.append(folder)

    # 面包屑导航，对于请求的目录找到其之前的目录，并添加url链接
    breadcrumb_list = [{'tag': '全部文件', 'uri': ''}]
    uri = ''
    for value in pdir.split('/'):
        if value:
            uri = uri + value + '/'
            breadcrumb_list.append({'tag': value, 'uri': uri})
    return render(request, 'webstroge/index.html',
                  {'index_list': index_list, 'username': str(user), 'breadcrumb_list': breadcrumb_list})


@login_required
def delete_file(request):
    # 数据收集，收集用户名，文件地址，当前目录
    user = str(request.user)
    user_id = User.objects.get(username=user).id
    file_path = request.GET.get('file_path')
    pwd = request.GET.get('pwd')

    # 找到数据库中的记录，并删除
    FileInfo.objects.filter(file_path=file_path, user_id=user_id).delete()

    # 尝试删除磁盘上的文件
    try:
        os.remove(PARENT_DIR + '/media/' + file_path)
    except Exception as e:
        print(e)
    # 重定向到当前目录
    return redirect('/pan/folder/?pdir=' + pwd)


@login_required
def rename_file(request):
    # 数据收集阶段，收集用户名，旧文件名，新文件名，当前目录
    user = str(request.user)
    user_id = User.objects.get(username=user).id
    old_file_name = request.GET.get('old_file_name')
    file_type = old_file_name.split('.')[-1]
    new_file_name = request.GET.get('new_file_name') + '.' + file_type
    pwd = request.GET.get('pwd')

    # 找到旧文件，旧地址
    file_obj = FileInfo.objects.get(belong_folder=pwd, file_name=old_file_name, user_id=user_id)
    old_path = file_obj.file_path

    # 更改为新地址
    new_path = old_path.replace(old_file_name, new_file_name)
    file_obj.file_path = new_path

    # 对磁盘上的文件更名，用os.rename
    old_full_path = PARENT_DIR + '/media/' + old_path
    new_full_path = PARENT_DIR + '/media/' + new_path
    os.rename(old_full_path, new_full_path)

    # 为数据库中的文件名更名，并保存
    file_obj.file_name = new_file_name
    file_obj.save()
    # 重定向到当前目录
    return redirect('/pan/folder/?pdir=' + pwd)


@login_required
def rename_folder(request):
    # 数据收集阶段，用户id，原文件名，新文件名，当前目录
    user = str(request.user)
    user_id = User.objects.get(username=user).id
    old_folder_name = request.GET.get('old_folder_name')
    new_folder_name = request.GET.get('new_folder_name')
    pwd = request.GET.get('pwd')

    # 找到要修改的文件夹
    folder_obj = FolderInfo.objects.get(belong_folder=pwd, folder_name=old_folder_name, user_id=user_id)
    folder_obj.folder_name = new_folder_name
    old_belong_folder = folder_obj.belong_folder + old_folder_name + '/'
    new_belong_folder = folder_obj.belong_folder + new_folder_name + '/'
    # 装配出相对该用户完整的地址
    old_full_path = os.path.join(PARENT_DIR, 'media', user, old_belong_folder)
    new_full_path = os.path.join(PARENT_DIR, 'media', user, new_belong_folder)
    os.rename(old_full_path, new_full_path)
    # 重命名文件夹
    # 找到所有在当前文件夹里的文件夹记录
    folder_belong_folder_objs = FolderInfo.objects.filter(belong_folder__startswith=old_belong_folder,
                                                          user_id=user_id)
    # 找到所有在此文件夹里的文件夹，并将其父目录改成新的文件夹名
    for folder_belong_folder_obj in folder_belong_folder_objs:
        tmp_belong_folder = folder_belong_folder_obj.belong_folder.replace(old_belong_folder, new_belong_folder)
        folder_belong_folder_obj.belong_folder = tmp_belong_folder
        folder_belong_folder_obj.save()
    file_belong_folder_objs = FileInfo.objects.filter(belong_folder__startswith=old_belong_folder,
                                                      user_id=user_id)
    # 找到所有在当前放文件夹里的文件记录，并将其父目录改成新的文件夹名
    for file_belong_folder_obj in file_belong_folder_objs:
        tmp_belong_folder = file_belong_folder_obj.belong_folder.replace(old_belong_folder, new_belong_folder)
        file_belong_folder_obj.belong_folder = tmp_belong_folder
        file_belong_folder_obj.save()
    folder_obj.save()
    return redirect('/pan/folder/?pdir=' + pwd)


@login_required
def delete_folder(request):
    username = request.user.username
    pwd = request.GET.get('pwd')
    folder_name = request.GET.get('folder_name') + '/'
    print(pwd, folder_name)
    try:
        # 删除当前文件夹
        # print(FolderInfo.objects.filter(folder_name=folder_name[:-1], belong_folder=pwd))
        FolderInfo.objects.filter(folder_name=folder_name[:-1], belong_folder=pwd).delete()
        # 删除当前文件夹的子文件夹
        # print(FolderInfo.objects.filter(belong_folder=pwd+folder_name))
        FolderInfo.objects.filter(belong_folder=pwd + folder_name).delete()
        # 删除当前文件夹的子文件
        # print(FileInfo.objects.filter(belong_folder=pwd+folder_name))
        FileInfo.objects.filter(belong_folder=pwd + folder_name).delete()
        # 删除当前文件夹的目录
        rm_dir = os.path.join(PARENT_DIR, 'media', username, pwd, folder_name)
        shutil.rmtree(rm_dir)
        # print(rm_dir)
    except Exception as e:
        print(e)
    return redirect('/pan/folder/?pdir=' + pwd)


@login_required
def mkdir(request):
    user = request.user
    user_id = User.objects.get(username=user).id
    pwd = request.GET.get('pwd')
    folder_name = request.GET.get('folder_name')
    # update_time = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
    update_time = timezone.now()
    try:
        user_path = os.path.join(PARENT_DIR, 'media', str(user))
        os.mkdir(user_path + '/' + pwd + folder_name)
        FolderInfo.objects.create(user_id=user_id, folder_name=folder_name, belong_folder=pwd,
                                  update_time=update_time)
    except Exception as e:
        print(e)
        info(request, "文件夹已存在")

    return redirect('/pan/folder/?pdir=' + pwd)


@login_required
def download_file(request):
    file_path = request.GET.get('file_path')
    file_name = file_path.split('/')[-1]
    file_dir = os.path.join(PARENT_DIR, 'media', file_path)
    file = open(file_dir, 'rb')
    response = FileResponse(file)
    response['Content-Type'] = 'application/octet-stream'
    response['Content-Disposition'] = 'attachment;filename={}'.format(urlquote(file_name))
    return response


@login_required
def upload_file(request):
    if request.method == "POST":
        user_name = str(request.user)
        user_obj = User.objects.get(username=user_name)
        file_obj = request.FILES.get('file')
        file_type = judge_filepath(file_obj.name.split('.')[-1].lower())
        pwd = request.POST.get('file_path')

        # update_time = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
        update_time = timezone.now()
        file_size = format_size(file_obj.size)
        file_name = file_obj.name
        # save_path = PARENT_DIR + '/media/' + user_name + '/' + pwd
        save_path = os.path.join(PARENT_DIR, 'media', user_name, pwd)

        file_path = user_name + '/' + pwd + file_name
        # print(belong_folder, folder_name, save_path)
        FileInfo.objects.create(user_id=user_obj.id, file_path=file_path,
                                file_name=file_name, update_time=update_time, file_size=file_size,
                                file_type=file_type, belong_folder=pwd)
        if not os.path.exists(save_path):
            os.mkdir(save_path)
        with open(save_path + file_name, 'wb+') as f:
            for chunk in file_obj.chunks():
                f.write(chunk)
        return redirect('/')


@login_required
def file_type(request):
    user = request.user
    file_type = request.GET.get('file_type')
    user_id = User.objects.get(username=user).id
    file_list = []
    if file_type == 'all':
        file_obj = FileInfo.objects.filter(user_id=user_id)
    else:
        file_obj = FileInfo.objects.filter(file_type=file_type, user_id=user_id)
    for file in file_obj:
        file_list.append({'file_path': file.file_path, 'file_name': file.file_name,
                          'update_time': str(file.update_time), 'file_size': file.file_size,
                          'file_type': file.file_type})
    return JsonResponse(file_list, safe=False)


@login_required
def search(request):
    file_type = request.GET.get('file_type')
    file_name = request.GET.get('file_name')
    user = request.user
    user_id = User.objects.get(username=user).id
    file_list = []
    if file_type == 'all':
        file_obj = FileInfo.objects.filter(file_name__icontains=file_name, user_id=user_id)
    else:
        file_obj = FileInfo.objects.filter(file_type=file_type, file_name__icontains=file_name, user_id=user_id)
    for file in file_obj:
        file_list.append({'file_path': file.file_path, 'file_name': file.file_name,
                          'update_time': str(file.update_time), 'file_size': file.file_size,
                          'file_type': file.file_type})
    return JsonResponse(file_list, safe=False)
