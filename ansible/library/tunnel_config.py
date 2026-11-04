from ansible.module_utils.basic import AnsibleModule
import traceback


def _parse_ipinip_tunnel(tunnel_param):
    """IPInIP tunnel (e.g. dualtor-aa's MuxTunnel0): dscp/ecn/ttl fields
    required, matching the original schema."""
    return {
        'type': tunnel_param['type'],
        'attach_to': tunnel_param['attach_to'],
        'dscp': tunnel_param['dscp'],
        'ecn_encap': tunnel_param['ecn_encap'],
        'ecn_decap': tunnel_param['ecn_decap'],
        'ttl_mode': tunnel_param['ttl_mode'],
    }


def _parse_vxlan_tunnel(tunnel_param):
    """Vxlan/EVPN tunnel (e.g. bgp-evpn-mh-lacp-dtor's VxlanTunnel0): no
    dscp/ecn/ttl concept, instead carries the VTEP source IP, the EVPN NVO
    name, and the L2VNI (vlan_vni_map) / L3VNI (vrf_vni_map) mappings.
    src_ip defaults to attach_to (Loopback0 is both the tunnel's attach point
    and its source IP in every example in this repo)."""
    return {
        'type': tunnel_param['type'],
        'attach_to': tunnel_param['attach_to'],
        'src_ip': tunnel_param.get('src_ip', tunnel_param['attach_to']),
        'evpn_nvo': tunnel_param.get('evpn_nvo'),
        'vlan_vni_map': tunnel_param.get('vlan_vni_map', {}),
        'vrf_vni_map': tunnel_param.get('vrf_vni_map', {}),
    }


_TUNNEL_TYPE_PARSERS = {
    'IPInIP': _parse_ipinip_tunnel,
    'Vxlan': _parse_vxlan_tunnel,
}


def main():
    module = AnsibleModule(
        argument_spec=dict(
            vm_topo_config=dict(required=True, type="dict"),
            tunnel_config=dict(required=False, type='str', default=None),
        ),
        supports_check_mode=True
    )
    m_args = module.params
    tunnel_config = m_args['tunnel_config']

    tunnel_configs = {}
    try:
        if 'tunnel_configs' in m_args['vm_topo_config']['DUT']:
            if tunnel_config is None or len(tunnel_config) == 0:
                tunnel_config = m_args['vm_topo_config']['DUT']['tunnel_configs']['default_tunnel_config']

            tunnels = m_args['vm_topo_config']['DUT']['tunnel_configs'][tunnel_config]
            for tunnel, tunnel_param in tunnels.items():
                tunnel_type = tunnel_param['type']
                parser = _TUNNEL_TYPE_PARSERS.get(tunnel_type)
                if parser is None:
                    module.fail_json(
                        msg="Unsupported tunnel type '%s' for tunnel '%s' "
                            "(supported: %s)" % (
                                tunnel_type, tunnel,
                                ', '.join(_TUNNEL_TYPE_PARSERS.keys())))
                tunnel_configs[tunnel] = parser(tunnel_param)

    except Exception:
        module.fail_json(msg=traceback.format_exc())
    else:
        module.exit_json(ansible_facts={'tunnel_configs': tunnel_configs})


if __name__ == "__main__":
    main()
