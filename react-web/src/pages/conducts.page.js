import React, { Component } from "react";

import configData from "./../config/config.json";

import ConductList from "./../components/conductList.component"

export default class Conducts extends Component {
    constructor(props) {
        super(props);
        this.state = {
            conducts : []
        }

        const requestOptions = {
            method: 'GET',
            credentials: 'include',
            mode: configData.cosMode
        };
        fetch(configData.url+configData.uri+'conducts/', requestOptions).then(response => {
            if (response.ok) {
                return response.json()
            }
        }).then(json => {
            this.setState({ conducts : json["results"] });
        });
    }

    render() {
        return (
            <div className="pageContent1">
                <ConductList conducts={this.state.conducts} />
            </div>
        );
    }
}