import collections
import copy

import click
import fmf

import tmt


class Prepare(tmt.steps.Step):
    """
    Prepare the environment for testing.

    Use the 'order' attribute to select in which order preparation
    should happen if there are multiple configs. Default order is '50'.
    Default order of required packages installation is '70', for the
    recommended packages it is '75'.
    """

    def __init__(self, data, plan):
        """ Initialize prepare step data """
        super().__init__(data, plan)
        self.preparations_applied = 0

    def wake(self):
        """ Wake up the step (process workdir and command line) """
        super().wake()

        # Choose the right plugin and wake it up
        for data in self.data:
            plugin = PreparePlugin.delegate(self, data)
            plugin.wake()
            # Add plugin only if there are data
            if len(plugin.data.keys()) > 2:
                self._plugins.append(plugin)

        # Nothing more to do if already done
        if self.status() == 'done':
            self.debug(
                'Prepare wake up complete (already done before).', level=2)
        # Save status and step data (now we know what to do)
        else:
            self.status('todo')
            self.save()

    def show(self):
        """ Show discover details """
        for data in self.data:
            PreparePlugin.delegate(self, data).show()

    def summary(self):
        """ Give a concise summary of the preparation """
        preparations = fmf.utils.listed(
            self.preparations_applied, 'preparation')
        self.info('summary', f'{preparations} applied', 'green', shift=1)

    def _prepare_roles(self):
        """ Create a mapping of roles to guest names """
        role_mapping = collections.defaultdict(list)
        for guest in self.plan.provision.guests():
            if guest.role:
                role_mapping[guest.role].append(guest.name)
        return role_mapping

    def _prepare_hosts(self):
        """ Create a mapping of guest names to IP addresses """
        host_mapping = {}
        for guest in self.plan.provision.guests():
            if hasattr(guest, 'guest') and guest.guest:
                host_mapping[guest.name] = guest.guest
        return host_mapping

    def go(self):
        """ Prepare the guests """
        super().go()

        # Nothing more to do if already done
        if self.status() == 'done':
            self.info('status', 'done', 'green', shift=1)
            self.summary()
            self.actions()
            return

        # Required packages
        requires = set(
            self.plan.discover.requires() +
            self.plan.provision.requires() +
            self.plan.execute.requires()
            )

        if requires:
            data = dict(
                how='install',
                name='requires',
                summary='Install required packages',
                order=tmt.utils.DEFAULT_PLUGIN_ORDER_REQUIRES,
                package=list(requires))
            self._plugins.append(PreparePlugin.delegate(self, data))

        # Recommended packages
        recommends = self.plan.discover.recommends()
        if recommends:
            data = dict(
                how='install',
                name='recommends',
                summary='Install recommended packages',
                order=tmt.utils.DEFAULT_PLUGIN_ORDER_RECOMMENDS,
                package=recommends,
                missing='skip')
            self._plugins.append(PreparePlugin.delegate(self, data))

        # Implicit multihost setup
        if len(self.plan.provision.guests()) > 1:
            data = dict(
                how='multihost',
                name='multihost',
                summary='Setup guest for multihost testing',
                roles=self._prepare_roles(),
                hosts=self._prepare_hosts(),
                )
            self._plugins.append(PreparePlugin.delegate(self, data))

        # Prepare guests (including workdir sync)
        for guest in self.plan.provision.guests():
            guest.push()
            # Create a guest copy and change its parent so that the
            # operations inside prepare plugins on the guest use the
            # prepare step config rather than provision step config.
            guest_copy = copy.copy(guest)
            guest_copy.parent = self
            # Execute each prepare plugin
            for plugin in self.plugins():
                if plugin.enabled_on_guest(guest_copy):
                    self.preparations_applied += 1
                    plugin.go(guest_copy)
                    self.info('')
            # Pull artifacts created in the plan data directory
            # if there was at least one plugin executed
            if self.plugins():
                guest_copy.pull(self.plan.data_directory)

        # Give a summary, update status and save
        self.summary()
        self.status('done')
        self.save()


class PreparePlugin(tmt.steps.Plugin):
    """ Common parent of prepare plugins """

    # List of all supported methods aggregated from all plugins
    _supported_methods = []

    # Common keys for all prepare step implementations
    _keys = ['on']

    @classmethod
    def base_command(cls, method_class=None, usage=None):
        """ Create base click command (common for all prepare plugins) """

        # Prepare general usage message for the step
        if method_class:
            usage = Prepare.usage(method_overview=usage)

        # Create the command
        @click.command(cls=method_class, help=usage)
        @click.pass_context
        @click.option(
            '-h', '--how', metavar='METHOD',
            help='Use specified method for environment preparation.')
        def prepare(context, **kwargs):
            context.obj.steps.add('prepare')
            Prepare._save_context(context)

        return prepare

    def go(self):
        super().go()
        on = self.get('on')
        if on:
            self.info('on', on, 'green')
