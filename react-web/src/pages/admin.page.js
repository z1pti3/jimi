import React, { Component } from "react";

import configData from "./../config/config.json";

import ClusterList from "./../components/clusterList.component"
import ClusterJobList from "./../components/clusterJobList.component"

import "../components/html.component.css"

import "./admin.page.css"

function apiClusterMembersRefresh() {
    const requestOptions = {
        method: 'GET',
        credentials: 'include',
        mode: configData.cosMode
    };
    var triggers = fetch(configData.url+configData.uri+'cluster/', requestOptions).then(response => {
        if (response.ok) {
            return response.json()
        }
    }).then(json => {
        return json["results"];
    });
    return triggers
}

function apiJobsRefresh() {
    const requestOptions = {
        method: 'GET',
        credentials: 'include',
        mode: configData.cosMode
    };
    var triggers = fetch(configData.url+configData.uri+'workers/', requestOptions).then(response => {
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
            clusterMembers : [],
            jobs : []
        }

        this.updateclusterMembers = this.updateClusterMembers.bind(this);
        this.updateJobs = this.updateJobs.bind(this);

        apiClusterMembersRefresh().then(clusterMembers => {
            this.setState({ clusterMembers : clusterMembers });
            this.updateClusterMembers();
        })

        apiJobsRefresh().then(jobs => {
            this.setState({ jobs : jobs });
            this.updateJobs();
        })
    }

    updateJobs() {
        setTimeout(() => {
            apiJobsRefresh().then(jobs => {
                this.setState({ jobs : jobs });
                this.updateJobs();
            })
        }, 5000 );
    }

    updateClusterMembers() {
        setTimeout(() => {
            apiClusterMembersRefresh().then(clusterMembers => {
                this.setState({ clusterMembers : clusterMembers });
                this.updateClusterMembers();
            })
        }, 15000 );
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
                <ClusterList clusterMembers={this.state.clusterMembers} />
                <br/>
                <br/>
                <h1>Job Status</h1>
                <hr/>
                <ClusterJobList jobs={this.state.jobs} />
            </div>
        );
    }
}
