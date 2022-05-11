from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse
from django.shortcuts import render, redirect
from .forms import CustomSignupForm
from django.urls import reverse_lazy
from django.views import generic
from django.contrib.auth import authenticate, login
from django.conf import settings
from .models import Customer
import stripe

stripe.api_key = settings.STRIPE_SECRET_KEY

def index(request):
    return HttpResponse("Welcome to our Membership website")


def home(request):
    return render(request, 'membership/home.html')

@login_required
def settings(request):
    membership = False
    cancel_at_period_end = False
    if request.method == 'POST':
        subscription = stripe.Subscription.retrieve(request.user.customer.stripe_subscription_id)
        subscription.cancel_at_period_end = True
        request.user.customer.cancel_at_period_end = True
        cancel_at_period_end = True
        subscription.save()
        request.user.customer.save()
    else:
        try:
            if request.user.customer.membership:
                membership = True
            if request.user.customer.cancel_at_period_end:
                cancel_at_period_end = True
        except Customer.DoesNotExist:
            membership = False
    return render(request, 'registration/settings.html', {'membership':membership,
    'cancel_at_period_end':cancel_at_period_end})


@user_passes_test(lambda u: u.is_superuser)
def updateaccounts(request):
    customers = Customer.objects.all()
    for customer in customers:
        subscription = stripe.Subscription.retrieve(customer.stripe_subscription_id)
        if subscription.status != 'active':
            customer.membership = False
        else:
            customer.membership = True
        customer.cancel_at_period_end = subscription.cancel_at_period_end
        customer.save()
    return HttpResponse('completed')


def Deletesubscription(request):
    stripe.Subscription.delete(stripe.Subscription.retrieve(request.user.customer.stripe_subscription_id)),
    return redirect('/deletemsg')


def deletemsg(request):
    return render(request, "deletemsg.html")



def update(request):
    current_subscription = stripe.Subscription.retrieve(request.user.customer.stripe_subscription_id)
    print(current_subscription)
    # new plan
    stripe.Subscription.modify(
        request.user.customer.stripe_subscription_id,
        cancel_at_period_end=True,
        proration_behavior='create_prorations',
        # the new subscription
        items=[{
            'id': current_subscription['items'].data[0].id,
            # note if you have more than one Plan per Subscription, you'll need to improve this. This assumes one plan per sub.
            'deleted': True,
        }, {
            'plan': 'price_1KxZTqSE5P0vwzLj5mUgsofY'
        }],
    )
    current_subscription = stripe.Subscription.retrieve(request.user.customer.stripe_subscription_id)
    print(current_subscription)
    return HttpResponse("updated successfully")






def pausepayment(request):
    stripe.Subscription.modify(
    request.user.customer.stripe_subscription_id,
    pause_collection={
        'behavior': 'mark_uncollectible',
    },
    )
    return redirect('/pausemsg')

def pausemsg(request):
    return render(request, "pausemsg.html")



def Resumepayment(request):
    stripe.Subscription.modify(
    request.user.customer.stripe_subscription_id,
    pause_collection='',
)
    return redirect('/resumemsg')


def resumemsg(request):
    return render(request, "resumemsg.html")



def join(request):
    return render(request, 'membership/join.html')


def success(request):
    if request.method == 'GET' and 'session_id' in request.GET:
        session = stripe.checkout.Session.retrieve(request.GET['session_id'],)
        customer = Customer()
        customer.user = request.user
        customer.stripeid = session.customer
        customer.membership = True
        customer.cancel_at_period_end = False
        customer.stripe_subscription_id = session.subscription
        customer.save()
    return render(request, 'membership/success.html')


def cancel(request):
    return render(request, 'membership/cancel.html')



@login_required
def checkout(request):

    try:
        if request.user.customer.membership:
            return redirect('settings')
    except Customer.DoesNotExist:
        pass

    if request.method == 'POST':
        pass
    else:
        membership = 'monthly'
        final_dollar = 10
        membership_id = 'price_1KxZTqSE5P0vwzLj7DDW79Nm'
        if request.method == 'GET' and 'membership' in request.GET:
            if request.GET['membership'] == 'yearly':
                membership = 'yearly'
                membership_id = 'price_1KxZTqSE5P0vwzLj5mUgsofY'
                final_dollar = 100

        # Create Strip Checkout
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            customer_email = request.user.email,
            line_items=[{
                'price': membership_id,
                'quantity': 1,
            }],
            mode='subscription',
            allow_promotion_codes=True,
            success_url='http://127.0.0.1:8000/success?session_id={CHECKOUT_SESSION_ID}',
            cancel_url='http://127.0.0.1:8000/cancel',
        )

        return render(request, 'membership/checkout.html', {'final_dollar': final_dollar, 'session_id': session.id})




class SignUp(generic.CreateView):
    form_class = CustomSignupForm
    success_url = reverse_lazy('home')
    template_name = 'registration/signup.html'

    def form_valid(self, form):
        valid = super(SignUp, self).form_valid(form)
        username, password = form.cleaned_data.get('username'), form.cleaned_data.get('password1')
        new_user = authenticate(username=username, password=password)
        login(self.request, new_user)
        return valid