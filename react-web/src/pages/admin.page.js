import React, { Component } from "react";

import configData from "./../config/config.json";

import StatusList from "./../components/status.component"

import "../components/html.component.css"

import "./admin.page.css"

function apiTriggerStatusRefresh() {
    const requestOptions = {
        method: 'GET',
        credentials: 'include',
        mode: configData.cosMode
    };
    var triggers = fetch(configData.url+configData.uri+'models/trigger/all/', requestOptions).then(response => {
        if (response.ok) {
            return response.json()
        }
    }).then(json => {
        return json["results"];
    });
    return triggers
}

export default class AdminPage extends Component {
    constructor(props) {
        super(props);
        this.state = {
            triggers : []
        }

        this.updateTriggers = this.updateTriggers.bind(this);

        apiTriggerStatusRefresh().then(triggers => {
            this.setState({ triggers : triggers });
            this.updateTriggers();
        })
    }

    updateTriggers() {
        setTimeout(() => {
            apiTriggerStatusRefresh().then(triggers => {
                this.setState({ triggers : triggers });
                this.updateTriggers();
            })
        }, 2500 );
    }

    render() {
        return (
            <div className="pageContent1">
                <h1>Controls</h1>
                <hr/>
                <button className="btn btn-primary btn-block button medium marSmall" onClick={this.NewConduct}>Clear Cache</button>
                <br/>
                <button className="btn btn-primary btn-block button medium marSmall" onClick={this.NewConduct}>Clear StartChecks</button>
                <br/>
                <button className="btn btn-primary btn-block button medium marSmall" onClick={this.NewConduct}>Redistribute Cluster</button>
                <br/>
                <button className="btn btn-primary btn-block button medium marSmall" onClick={this.NewConduct}>Backup</button>
                <br/>
                <button className="btn btn-primary btn-block button medium marSmall" onClick={this.NewConduct}>Delete Unused Objects</button>
                <br/>
                <br/>
                <h1>Cluster Status</h1>
                <hr/>
                <br/>
            </div>
        );
    }
}
