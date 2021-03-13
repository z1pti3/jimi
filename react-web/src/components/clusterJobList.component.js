import React, { Component } from "react";
import ClusterJobItem from "./clusterJobItem.component"

import "./html.component.css"
import "./clusterJobList.component.css"

function ClusterJobList(props) {
    return (
        <div className="clusterJobListContainer">
            {props.jobs ? props.jobs.map(c => <ClusterJobItem key={c.id} id={c.id} server={c.server} createdTime={c.createdTime} name={c.name} startTime={c.startTime} />) : null }
        </div>
    )
}

export default ClusterJobList;