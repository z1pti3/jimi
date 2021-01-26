import React, { Component } from "react";
import { useHistory } from 'react-router-dom';

import configData from "./../config/config.json";
import { URL } from"./../utils/api";

import ClusterList from "./../components/clusterList.component"
import ClusterJobList from "./../components/clusterJobList.component"

import "../components/html.component.css"

import "./admin.page.css"

function apiClusterMembersRefresh() {
    const requestOptions = {
        method: 'GET',
        credentials: 'include',
    };
    var triggers = fetch(URL()+'cluster/', requestOptions).then(response => {
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
    };
    var triggers = fetch(URL()+'workers/', requestOptions).then(response => {
        if (response.ok) {
            return response.json()
        }
    }).then(json => {
        return json["results"];
    });
    return triggers
}

export default class AdminPage extends Component {
    timeoutIDclusterMembers;
    timeoutIDJobs;
    constructor(props) {
        super(props);
        this.state = {
            clusterMembers : [],
            jobs : []
        }

        this.updateclusterMembers = this.updateClusterMembers.bind(this);
        apiClusterMembersRefresh().then(clusterMembers => {
            this.setState({ clusterMembers : clusterMembers });
            this.updateClusterMembers();
        })

        this.updateJobs = this.updateJobs.bind(this);
        apiJobsRefresh().then(jobs => {
            this.setState({ jobs : jobs });
            this.updateJobs();
        })

        this.clearCache = this.clearCache.bind(this);
        this.clearStartChecks = this.clearStartChecks.bind(this);
        this.redistributeCluster = this.redistributeCluster.bind(this);
        this.deleteUnusedObjects = this.deleteUnusedObjects.bind(this);
    }

    componentWillUnmount() {
        clearTimeout(this.timeoutIDclusterMembers);
        clearTimeout(this.timeoutIDJobs);
    }

    updateJobs() {
        this.timeoutIDJobs = setTimeout(() => {
            apiJobsRefresh().then(jobs => {
                this.setState({ jobs : jobs });
                this.updateJobs();
            })
        }, 2500 );
    }

    updateClusterMembers() {
        this.timeoutIDclusterMembers = setTimeout(() => {
            apiClusterMembersRefresh().then(clusterMembers => {
                this.setState({ clusterMembers : clusterMembers });
                this.updateClusterMembers();
            })
        }, 15000 );
    }

    clearCache() {
        const requestOptions = {
            method: 'GET',
            credentials: 'include',
        };
        var triggers = fetch(URL()+'clearCache/', requestOptions).then(response => {
            if (response.ok) {
                return response.json()
            }
        }).then(json => {
            alert(JSON.stringify(json["results"]));
        });
    }

    clearStartChecks() {
        const requestOptions = {
            method: 'GET',
            credentials: 'include',
        };
        var triggers = fetch(URL()+'clearStartChecks/', requestOptions).then(response => {
            if (response.ok) {
                return response.json()
            }
        }).then(json => {
            alert(JSON.stringify(json));
        });
    }

    redistributeCluster() {
        const requestOptions = {
            method: 'GET',
            credentials: 'include',
        };
        var triggers = fetch(URL()+'cluster/distribute/', requestOptions).then(response => {
            if (response.ok) {
                return response.json()
            }
        }).then(json => {
            alert(JSON.stringify(json));
        });
    }

    deleteUnusedObjects() {
        this.props.history.push('/cleanup/'); 
    }

    render() {
        return (
            <div className="pageContent1">
                <h1>Controls</h1>
                <hr/>
                <button className="btn btn-primary btn-block button medium marSmall" onClick={this.clearCache}>Clear Cache</button>
                <br/>
                <button className="btn btn-primary btn-block button medium marSmall" onClick={this.clearStartChecks}>Clear StartChecks</button>
                <br/>
                <button className="btn btn-primary btn-block button medium marSmall" onClick={this.redistributeCluster}>Redistribute Cluster</button>
                <br/>
                <button className="btn btn-primary btn-block button medium marSmall" onClick={this.deleteUnusedObjects}>Delete Unused Objects</button>
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
