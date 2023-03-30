import time


class DjStripeHTTPClient:
    """ """

    def _should_retry(self, stripe_default_client, error, num_retries, kwargs_dict):
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

        if headers is not None and headers.get("idempotent-replayed") == "true":
            # https://github.com/stripe/stripe-ruby/pull/907
            # Stripe simply replays the error if a previous erroneous request was made
            # Hence resetting the idempotency_key to create a "new" request
            kwargs_dict["idempotency_key"] = kwargs_dict.get(
                "metadata", {"idempotency_key": None}
            )["idempotency_key"] = None

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
            return True

        return False

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

            if self._should_retry(default_http_client, error, num_retries, kwargs):
                num_retries += 1
                sleep_time = default_http_client._sleep_time_seconds(num_retries)

                print(f"retrying request {self}, {func}")
                print(f"sleeping for {sleep_time} seconds")
                time.sleep(sleep_time)

            else:
                raise error


djstripe_client = DjStripeHTTPClient()
