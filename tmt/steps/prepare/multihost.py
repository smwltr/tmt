import tmt.utils


class PrepareMultihost(tmt.steps.prepare.PreparePlugin):
    """
    Prepare the guest for running a multihost test.

    This step is enabled implicitly, when multiple guests are detected in
    the plan. It exports the information about guest roles and updates
    /etc/hosts accordingly. Default order is '65'.

    This method requires specifying roles and hosts. The expected format is
    the following:

    roles:
      - server:
          - server-one
          - server-two

    hosts:
      - server-one: 10.10.10.10
      - server-two: 10.10.10.11

    The exported roles are comma-separated.
    """

    # Supported methods
    _methods = [tmt.steps.Method(
        name='multihost',
        doc=__doc__,
        order=tmt.utils.DEFAULT_PLUGIN_ORDER_MULTIHOST)]

    # Supported keys
    _keys = ['roles', 'hosts']

    def default(self, option, default=None):
        """ Return default data for given option """
        if option in ('roles', 'hosts'):
            return {}
        return default

    def go(self, guest):
        """ Prepare the guests """
        super().go(guest)

        self.debug('Export roles.', level=2)
        for role, corresponding_guests in self.get('roles').items():
            formatted_guests = ','.join(corresponding_guests)
            self.step.plan.environment[role] = formatted_guests
        self.debug("Add hosts to '/etc/hosts'.", level=2)
        for host_name, host_address in self.get('hosts').items():
            if host_address:
                guest.execute(
                    f'echo "{host_address} {host_name}" >> /etc/hosts')
