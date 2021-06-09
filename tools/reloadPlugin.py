import jimi, requests

def reloadModule(module):
    # Apply system updates
    clusterMembers = jimi.cluster.getAll()
    for clusterMember in clusterMembers:
        headers = { "x-api-token" : jimi.auth.generateSystemSession() }
        requests.get("{0}{1}system/update/{2}/".format(clusterMember,jimi.api.base,jimi.cluster.getMasterId()),headers=headers, timeout=60)
        requests.get("{0}{1}system/reload/module/{2}/".format(clusterMember,jimi.api.base,module),headers=headers, timeout=60)