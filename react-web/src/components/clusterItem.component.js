import React, { Component } from "react";
import PropTypes from "prop-types";

import { URL } from"./../utils/api";

import "./html.component.css"
import "./clusterItem.component.css"

function recalculateChecksum(systemID) {
    if (window.confirm('Are you sure you want to recalculate the checksum on system '+systemID+'?')) {
        const requestOptions = {
            method: 'GET',
            credentials: 'include',
        };
        fetch(URL()+'system/checksum/'+systemID+"/", requestOptions).then(response => {
            if (response.ok) {
                return response.json()
            }
        }).then(json => {
            alert(JSON.stringify(json));
        });
    }
}

function triggerUpdate(systemID) {
    var pullFromSystemID = window.prompt("Updated system "+systemID+" from which system i.e. 0?");
    if (pullFromSystemID) {
        const requestOptions = {
            method: 'GET',
            credentials: 'include',
        };
        fetch(URL()+'system/update/'+systemID+"/"+pullFromSystemID+"/", requestOptions).then(response => {
            if (response.ok) {
                return response.json()
            }
        }).then(json => {
            alert(JSON.stringify(json));
        });
    }
}

function ClusterJobItem(props) {
    var d = new Date(0);
    const now = Date.now()/1000;
    d.setUTCSeconds(props.lastSyncTime)
    return (
        <div className="clusterItemContainer">
            <div className="clusterItem">
                <div className="clusterLeft">
                    <p className="clusterTitle">{props.systemID} - {props.systemUID}</p>
                    <br/>
                    <p className="clusterLeftItem">Address: {props.bindSecure ? "https://" : "http://"}{props.bindAddress}:{props.bindPort}</p>
                    <br/>
                    <p className="clusterLeftItem">Checksum: <a href="#" onClick={() => {recalculateChecksum(props.systemID)}}>{props.checksum}</a></p>
                    <br/>
                    <p className="clusterLeftItem">Status: {props.lastSyncTime > now - 120 ? "Online" : "Offline" }</p>
                </div>
                <div className="clusterRight">
                    <p className="clusterRightItem">Last Sync: {d.toLocaleString()}</p>
                    <br/>
                    <p className="clusterRightItem">Sync Count: {props.syncCount}</p>
                    <br/>
                    <p className="clusterRightItem">Master: {props.master ? "Yes" : "No"}</p>
                    <br/>
                    <p className="clusterRightItem"><a href="#" onClick={() => {triggerUpdate(props.systemID)}}>Update</a></p>
                </div>
            </div>       
        </div>
    )
}

export default ClusterJobItem;