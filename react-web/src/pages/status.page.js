import React, { Component } from "react";

import configData from "./../config/config.json";
import { URL } from"./../utils/api";

import StatusList from "./../components/status.component"
import Loading from "./../components/loading.component"

import "./status.page.css"

var showDisabled = false;
var showCluster = false;

function apiTriggerStatusRefresh() {
    const requestOptions = {
        method: 'GET',
        credentials: 'include',
    };
    var triggers = fetch(URL()+'models/trigger/all/', requestOptions).then(response => {
        if (response.ok) {
            return response.json()
        }
    }).then(json => {
        return json["results"];
    });
    return triggers
}

export default class StatusPage extends Component {
    constructor(props) {
        super(props);
        this.state = {
            triggers : [],
            loading: true
        }
        this.mounted = true;

        this.updateTriggers = this.updateTriggers.bind(this);

        apiTriggerStatusRefresh().then(triggers => {
            this.setState({ triggers : triggers, loading: false });
            this.updateTriggers();
        })
    }

    componentWillUnmount() {
        this.mounted = false;
    }

    updateTriggers() {
        if (this.mounted) {
            setTimeout(() => {
                apiTriggerStatusRefresh().then(triggers => {
                    this.setState({ triggers : triggers });
                    this.updateTriggers();
                })
            }, 500 );
        }
    }

    toggleDisabled() {
        if (showDisabled) { showDisabled = false; } 
        else { showDisabled = true; }
    }

    toggleCluster() {
        if (showCluster) { showCluster = false; } 
        else { showCluster = true; }
    }

    render() {
        return !this.state.loading ? (
            <div className="pageContent1">
                <h1>Trigger Status</h1>
                <hr/>
                <button className="btn btn-primary btn-block button medium marSmall" onClick={this.toggleDisabled}>Toggle Disabled</button><br/>
                <button className="btn btn-primary btn-block button medium marSmall" onClick={this.toggleCluster}>Toggle Cluster</button>
                <br/>
                <br/>
                <div className="pageCenter-outer">
                    <div className="pageCenter-inner">
                        <StatusList triggers={this.state.triggers} showDisabled={showDisabled} showCluster={showCluster} />
                    </div>
                </div>
            </div>
        ) : <Loading />
    }
}
