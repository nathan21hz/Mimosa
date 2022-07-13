def do_render(push_config, data, hist_data):
    print(data, hist_data)
    curr_hosts = set(data[0])
    hist_hosts = set(hist_data[0])
    hosts_joined = curr_hosts - hist_hosts
    hosts_left = hist_hosts - curr_hosts
    print(hosts_joined, hosts_left)
    if len(hosts_joined) >0 or len(hosts_left)>0:
        hosts_joined_text = ", ".join(hosts_joined)
        hosts_left_text = ", ".join(hosts_left)
        return [1, hosts_joined_text, hosts_left_text]
    else:
        return [0, "", ""]