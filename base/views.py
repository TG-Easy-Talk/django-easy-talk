from django.shortcuts import render
from django.http import JsonResponse
import random
import time
from agora_token_builder import RtcTokenBuilder
from .models import RoomMember
import json
from django.views.decorators.csrf import csrf_exempt
import logging

logger = logging.getLogger(__name__)


def lobby(request):
    return render(request, 'base/lobby.html')


def room(request):
    return render(request, 'base/room.html')


def getToken(request):
    appId = "5c894664474548608bf0dfc4cd6c5c1e"
    appCertificate = "5bb7dd8e48b9451f8aead98178bfd117"
    channelName = request.GET.get('channel')
    uid = random.randint(1, 230)
    expirationTimeInSeconds = 3600
    currentTimeStamp = int(time.time())
    privilegeExpiredTs = currentTimeStamp + expirationTimeInSeconds
    role = 1

    token = RtcTokenBuilder.buildTokenWithUid(appId, appCertificate, channelName, uid, role, privilegeExpiredTs)

    return JsonResponse({'token': token, 'uid': uid}, safe=False)


@csrf_exempt
def createMember(request):
    try:
        data = json.loads(request.body)
        name = data.get('name')
        room_name = data.get('room_name')
        uid = data.get('UID')

        member, created = RoomMember.objects.get_or_create(
            uid=uid,
            room_name=room_name,
            defaults={'name': name}
        )
        if not created:
            member.name = name
            member.save()

        return JsonResponse({'name': member.name}, status=200)
    except Exception as e:
        logger.exception("Erro ao criar membro")
        return JsonResponse({'error': str(e)}, status=500)


def getMember(request):
    uid = request.GET.get('UID')
    room_name = request.GET.get('room_name')

    member = RoomMember.objects.get(
        uid=uid,
        room_name=room_name,
    )
    name = member.name
    return JsonResponse({'name': member.name}, safe=False)


@csrf_exempt
def deleteMember(request):
    data = json.loads(request.body)
    member = RoomMember.objects.get(
        name=data['name'],
        uid=data['UID'],
        room_name=data['room_name']
    )
    member.delete()
    return JsonResponse('Member deleted', safe=False)
