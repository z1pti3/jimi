import React, { Component } from "react";

import configData from "./../config/config.json";

import StatusList from "./../components/status.component"

import "./status.page.css"

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

export default class Status extends Component {
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
                <h1>Trigger Status:</h1>
                <br/>
                <StatusList triggers={this.state.triggers} />
            </div>
        );
    }
}
