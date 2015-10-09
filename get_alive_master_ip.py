from kazoo.client import KazooClient


def run(zk_conn_str):
    zk = KazooClient(hosts=zk_conn_str)
    zk.start()
    try:
        master_ip = zk.get("/spark/leader_election/current_master")[0].decode('utf-8')
        zk.stop()
    except:
        master_ip = ""
        zk.stop()
    return master_ip
