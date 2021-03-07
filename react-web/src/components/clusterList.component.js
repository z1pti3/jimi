import React, { Component } from "react";
import ClusterItem from "./clusterItem.component"

import "./html.component.css"
import "./clusterList.component.css"

function ClusterList(props) {
    return (
        <div>
            {props.clusterMembers.map(c => <ClusterItem key={c._id} id={c._id} systemID={c.systemID} systemUID={c.systemUID} lastSyncTime={c.lastSyncTime} master={c.master} syncCount={c.syncCount} bindSecure={c.bindSecure} bindAddress={c.bindAddress} bindPort={c.bindPort} checksum={c.checksum} />)}
        </div>
    )
}

export default ClusterList;