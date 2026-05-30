from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated, BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from .models import CustomUser, Address
from .serializers import (
    B2BTokenObtainPairSerializer, UserSerializer,
    RegisterSerializer, AddressSerializer,
    AgentBuyerSerializer, RequestAccessSerializer,
)


class IsAgent(BasePermission):
    message = 'Agent access required.'

    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.is_agent
        )


class B2BTokenObtainPairView(TokenObtainPairView):
    serializer_class = B2BTokenObtainPairSerializer


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response({'error': 'Refresh token required.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            RefreshToken(refresh_token).blacklist()
        except TokenError:
            return Response({'error': 'Invalid or expired token.'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'message': 'Logged out successfully.'}, status=status.HTTP_200_OK)


class RegisterView(generics.CreateAPIView):
    queryset           = CustomUser.objects.all()
    permission_classes = [AllowAny]
    serializer_class   = RegisterSerializer


class RequestAccessView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RequestAccessSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response(
            {'message': 'Access request submitted. Our team will contact you shortly.'},
            status=status.HTTP_201_CREATED,
        )


class ProfileView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class   = UserSerializer

    def get_object(self):
        return self.request.user


class AddressListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class   = AddressSerializer

    def get_queryset(self):
        user      = self.request.user
        buyer_id  = self.request.query_params.get('buyer_id')
        if user.is_agent and buyer_id:
            try:
                buyer = user.assigned_buyers.get(pk=buyer_id, is_verified_b2b=True)
                return Address.objects.filter(user=buyer)
            except Exception:
                pass
        return Address.objects.filter(user=user)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class AddressDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class   = AddressSerializer

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)


class AgentCanOrderToggleView(APIView):
    """
    Feature 1: Buyer toggles permission for their assigned agent to place
    orders on their behalf.
    GET  /api/accounts/agent-can-order/  -- get current setting
    PATCH /api/accounts/agent-can-order/ { "agent_can_order": true/false }
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({
            'agent_can_order': user.agent_can_order,
            'assigned_agent':  user.assigned_agent.email if user.assigned_agent else None,
        })

    def patch(self, request):
        user = request.user
        if user.is_agent:
            return Response(
                {'error': 'Agents cannot toggle this setting.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not user.assigned_agent:
            return Response(
                {'error': 'You do not have an assigned agent.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        value = request.data.get('agent_can_order')
        if value is None or not isinstance(value, bool):
            return Response(
                {'error': 'agent_can_order must be true or false.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.agent_can_order = value
        user.save(update_fields=['agent_can_order'])
        return Response({
            'agent_can_order': user.agent_can_order,
            'assigned_agent':  user.assigned_agent.email,
            'message': f"Agent ordering {'enabled' if value else 'disabled'} successfully.",
        })


class AgentBuyersListView(generics.ListAPIView):
    permission_classes = [IsAgent]
    serializer_class   = AgentBuyerSerializer

    def get_queryset(self):
        return CustomUser.objects.filter(
            assigned_agent=self.request.user,
            is_verified_b2b=True,
        ).order_by('-date_joined')


class AgentBuyerDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAgent]
    serializer_class   = AgentBuyerSerializer

    def get_queryset(self):
        return CustomUser.objects.filter(assigned_agent=self.request.user)


class AgentManualOnboardView(APIView):
    permission_classes = [IsAgent]

    def post(self, request):
        email        = request.data.get('email', '').strip().lower()
        first_name   = request.data.get('first_name', '').strip()
        last_name    = request.data.get('last_name', '').strip()
        company_name = request.data.get('company_name', '').strip()
        phone_number = request.data.get('phone_number', '').strip()
        gst_number   = request.data.get('gst_number', '').strip()

        if not email or not company_name or not phone_number:
            return Response(
                {'error': 'Email, company name, and phone number are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if CustomUser.objects.filter(email=email).exists():
            return Response(
                {'error': 'A user with this email already exists.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        temp_password = CustomUser.objects.make_random_password(length=12)

        user = CustomUser(
            email           = email,
            username        = email,
            first_name      = first_name,
            last_name       = last_name,
            company_name    = company_name,
            phone_number    = phone_number,
            gst_number      = gst_number or None,
            is_verified_b2b = True,
            assigned_agent  = request.user,
        )
        user.set_password(temp_password)
        user.save()

        return Response(
            {
                'message':       f'Buyer {email} onboarded successfully.',
                'buyer_id':      user.id,
                'email':         user.email,
                'company_name':  user.company_name,
                'temp_password': temp_password,
            },
            status=status.HTTP_201_CREATED,
        )