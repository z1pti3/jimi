import React, { Component } from "react";
import ConductItem from "./conductItem.component"

import "./html.component.css"
import "./status.component.css"

function StatusItem(props) {
    const now = Date.now()/1000;
    return (
        <div className="statusItemContainer">
            <div className={`statusItem ${props.enabled ? "statusItemEnabled" : "statusItemDisabled"} ${ ((props.startCheck > 0 && props.startCheck + props.maxDuration > now) || props.lastCheck + 2.5 > now) ? "statusItemRunning" : ""} ${props.enabled && props.startCheck > 0 && props.startCheck + props.maxDuration < now  ? "statusItemCrashed" : ""} `} title={props.name}>
            </div>       
        </div>
    )
}

function StatusList(props) {
    if (props.showDisabled == false)
    {
        var tempTriggers = [];
        for (var i=0;i<props.triggers.length;i++)
        {
            if (props.triggers[i].enabled) { tempTriggers.push(props.triggers[i]) }
        }
        props.triggers = tempTriggers;
    }
    if (props.showCluster)
    {
        var clusterDict = {};
        for (var i=0;i<props.triggers.length;i++)
        {
            if (!clusterDict[props.triggers[i].systemID]) 
            { 
                clusterDict[props.triggers[i].systemID] = []; 
            }
            clusterDict[props.triggers[i].systemID].push(props.triggers[i]) 
        }
        return(
            Object.entries(clusterDict).map(([key,value]) =>
                <div>
                    <h2 key={key}>System {key}</h2>
                    {value.map(c => <StatusItem key={c._id} name={c.name} enabled={c.enabled} startCheck={c.startCheck} lastCheck={c.lastCheck} maxDuration={c.maxDuration == 0 ? 60 : c.maxDuration} />)}
                    <span>&nbsp;&nbsp;</span>
                    <br/>
                </div>
            )
        )
    }
    return (
        <div>
            {props.triggers.map(c => <StatusItem key={c._id} name={c.name} enabled={c.enabled} startCheck={c.startCheck} lastCheck={c.lastCheck} maxDuration={c.maxDuration == 0 ? 60 : c.maxDuration} />)}
        </div>
    )
}

export default StatusList;