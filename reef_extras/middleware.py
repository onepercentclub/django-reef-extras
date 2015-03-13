from django.shortcuts import render_to_response
from django.template import RequestContext

from lockdown.middleware import (LockdownMiddleware as BaseLockdownMiddleware, 
                                _default_url_exceptions, _default_form)

from lockdown import settings


class LockdownMiddleware(BaseLockdownMiddleware):
    """
    LockdownMiddleware taken from the Django Lockdown package with the addition 
    of password coming from request header: X-Lockdown
    """
    def process_request(self, request):
        if not request.META.has_key('HTTP_CONNECTION'):
            return None

        try:
            session = request.session
        except AttributeError:
            raise ImproperlyConfigured('django-lockdown requires the Django '
                                       'sessions framework')

        # Don't lock down if the URL matches an exception pattern.
        if self.url_exceptions is None:
            url_exceptions = _default_url_exceptions
        else:
            url_exceptions = self.url_exceptions
        for pattern in url_exceptions:
            if pattern.search(request.path):
                return None

        # Don't lock down if outside of the lockdown dates.
        if self.until_date is None:
            until_date = settings.UNTIL_DATE
        else:
            until_date = self.until_date
        if self.after_date is None:
            after_date = settings.AFTER_DATE
        else:
            after_date = self.after_date
        if until_date or after_date:
            locked_date = False
            if until_date and datetime.datetime.now() < until_date:
                locked_date = True
            if after_date and datetime.datetime.now() > after_date:
                locked_date = True
            if not locked_date:
                return None

        form_data = request.method == 'POST' and request.POST or {}
        passwords = (request.META['HTTP_CONNECTION'],)

        if self.form is None:
            form_class = _default_form
        else:
            form_class = self.form

        form = form_class(passwords=passwords, data=form_data, **self.form_kwargs)

        authorized = False
        token = session.get(self.session_key)
        if hasattr(form, 'authenticate'):
            if form.authenticate(token):
                authorized = True
        elif token is True:
            authorized = True

        if authorized and self.logout_key and self.logout_key in request.GET:
            if self.session_key in session:
                del session[self.session_key]
            url = request.path
            querystring = request.GET.copy()
            del querystring[self.logout_key]
            if querystring:
                url = '%s?%s' % (url, querystring.urlencode())
            return self.redirect(request)

        # Don't lock down if the user is already authorized for previewing.
        if authorized:
            return None

        if form.is_valid():
            if hasattr(form, 'generate_token'):
                token = form.generate_token()
            else:
                token = True
            session[self.session_key] = token
            return self.redirect(request)

        page_data = {'until_date': until_date, 'after_date': after_date}
        if not hasattr(form, 'show_form') or form.show_form():
            page_data['form'] = form

        return render_to_response('lockdown/form.html', page_data,
                                  context_instance=RequestContext(request))
