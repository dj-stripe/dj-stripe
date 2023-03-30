import time


class DjStripeHTTPClient:
    """ """

    def __init__(self) -> None:
        print("INITIALISING djstripe_client")

    # todo need to also handle the error below

    #   rbody = '{\n  "error": {\n    "message": "Sorry, you\'re creating accounts too quickly. You should limit your requests to less...ttps://dashboard.stripe.com/test/logs/req_ZAVDH9HMp5H38K?t=1679369008",\n    "type": "invalid_request_error"\n  }\n}\n'
    #   rcode = 400
    #   resp = OrderedDict([('error', OrderedDict([('message', "Sorry, you're creating accounts too quickly. You should limit your re...url', 'https://dashboard.stripe.com/test/logs/req_ZAVDH9HMp5H38K?t=1679369008'), ('type', 'invalid_request_error')]))])
    #   rheaders = {'Server': 'nginx', 'Date': 'Tue, 21 Mar 2023 03:23:28 GMT', 'Content-Type': 'application/json', 'Content-Length': '34...: 'false', 'Stripe-Version': '2020-08-27', 'Strict-Transport-Security': 'max-age=63072000; includeSubDomains; preload'}

    #   rbody = '{"error":{"code":"rate_limit","doc_url":"https://stripe.com/docs/error-codes/rate-limit","message":"Testmode request ...mode. You can learn more about rate limits here https://stripe.com/docs/rate-limits.","type":"invalid_request_error"}}'
    #   rcode = 429
    #   resp = OrderedDict([('error', OrderedDict([('code', 'rate_limit'), ('doc_url', 'https://stripe.com/docs/error-codes/rate-limi...ou can learn more about rate limits here https://stripe.com/docs/rate-limits.'), ('type', 'invalid_request_error')]))])
    #   rheaders = {'Server': 'nginx', 'Date': 'Tue, 21 Mar 2023 03:23:39 GMT', 'Content-Type': 'application/json', 'Content-Length': '30...no-store', 'Stripe-Version': '2020-08-27', 'Strict-Transport-Security': 'max-age=63072000; includeSubDomains; preload'}

    def _should_retry(self, stripe_default_client, error, num_retries):
        max_network_retries = stripe_default_client._max_network_retries() or 3

        print(
            f"Should Retry? retries: {num_retries}, max_retries: {max_network_retries}"
        )
        if num_retries >= max_network_retries:
            return False

        http_status = error.http_status
        headers = error.headers
        message = error.user_message

        print(f"http_status: {http_status}, headers: {headers}, message: {message}")

        # TODO IN case of too many accounts creation error stripe-should-retry header is sent back as False!
        # TODO Need to bypass the headers block in case of pytest and set different values for max delay and initial delay params
        # # The API may ask us not to retry (eg; if doing so would be a no-op)
        # # or advise us to retry (eg; in cases of lock timeouts); we defer to that.
        # #
        # # Note that we expect the headers object to be a CaseInsensitiveDict, as is the case with the requests library.
        # if headers is not None and "stripe-should-retry" in headers:
        #     if headers["stripe-should-retry"] == "false":
        #         return False
        #     if headers["stripe-should-retry"] == "true":
        #         return True

        # Retry on Rate Limit errors.
        if http_status == 429 or (
            http_status == 400 and "limit your requests" in message
        ):
            stripe_default_client.INITIAL_DELAY = 1.25
            stripe_default_client.MAX_DELAY = 5
            return True

        return False

    # todo this needs to also support callbacks
    def _request_with_retries(
        self,
        func,
        id="",
        **kwargs,
    ) -> dict:
        from stripe import default_http_client

        num_retries = 0

        while True:
            try:
                if id:
                    response = func(id, **kwargs)
                else:
                    response = func(**kwargs)

                print("GOT RESPONSE!")
                return response
            except Exception as e:
                error = e

            if self._should_retry(default_http_client, error, num_retries):
                num_retries += 1
                sleep_time = default_http_client._sleep_time_seconds(num_retries)

                print(f"retrying request {self}, {func}")
                print(f"sleeping for {sleep_time} seconds")
                time.sleep(sleep_time)

            else:
                raise error


print("About to initialise djstripe_client")
djstripe_client = DjStripeHTTPClient()
